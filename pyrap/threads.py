import threading
# from pyrap import session
import pyrap
import ctypes
import inspect
import time
from pyrap.utils import out, ifnone
from threading import _active_limbo_lock, _active, _limbo,\
    _trace_hook, _profile_hook, _get_ident, Lock, _allocate_lock, \
    _start_new_thread, _Verbose
import sys
import traceback
import random


class ThreadInterrupt(Exception): pass

def iteractive():
    '''Returns a generator of tuples of thread ids and respective thread objects
    of threads that are currently active.'''
    for tid, tobj in threading._active.iteritems():
        yield tid, tobj

def active():
    '''Returns a dict of active local threads, which maps the thread ID to
    the respective thread object.'''
    return dict(list(iteractive()))

def sessionthreads():
    d = {}
    for i, t in iteractive():
        if isinstance(t, SessionThread):
            d[i] = t
    return d

def sleep(sec):
    '''Interruptable sleep'''
    ev = Event(verbose=0)
    ev.wait(sec)
    

thisthread = threading.current_thread

def Lock(verbose=None):
    return _Lock(verbose=verbose)


class _Lock(_Verbose):
    '''A reimplementation of a lock that is interruptable.'''
    
    def __init__(self, verbose=None):
        _Verbose.__init__(self, verbose)
        self.__lock = threading.Lock()
        self.__owner = None
        self.__cancel = False
        
    def cancel(self):
        self.__cancel = True
        if thisthread() is self.owner:
            self.release() 
        
    @property
    def owner(self):
        return self.__owner
    
    @property
    def canceled(self):
        return self.__cancel
    
        
    def acquire(self, timeout=None):
        delay = 0.0005
        endtime = time.time() + ifnone(timeout, 0)
        while True:
            gotit = self.__lock.acquire(0)
            if gotit or timeout == 0: 
                if gotit: self.__owner = threading.current_thread()
                break
            remaining = endtime - time.time()
            if remaining <= 0 and (timeout is not None) or self.__cancel:
                break
            if remaining < 0:
                remaining = .05
            delay = min(delay * 2, remaining, .05)
            time.sleep(delay)
        if self.canceled: 
            raise ThreadInterrupt()
        if gotit:
            if __debug__:
                self._note('%s.acquire(%s): successful' % (self, timeout))
            self.__owner = thisthread()
        return gotit
        
        
    def release(self):
        if self.owner is not thisthread():
            raise RuntimeError('cannot acquire un-allocated lock.')
        self.__owner = None
        self.__lock.release()
        
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, e, t, tb):
        self.release()
        
        
        
def RLock(*args, **kwargs):
    """Factory function that returns a new reentrant lock.

    A reentrant lock must be released by the thread that acquired it. Once a
    thread has acquired a reentrant lock, the same thread may acquire it again
    without blocking; the thread must release it once for each time it has
    acquired it.

    """
    return _RLock(*args, **kwargs)


class _RLock(_Verbose):
    """A reentrant lock must be released by the thread that acquired it. Once a
       thread has acquired a reentrant lock, the same thread may acquire it
       again without blocking; the thread must release it once for each time it
       has acquired it.
    """

    def __init__(self, verbose=None):
        _Verbose.__init__(self, verbose)
        self.__block = Lock()
        self.__count = 0
        self.__owner = None


    def __repr__(self):
        owner = self.__owner
        try:
            owner = _active[owner].name
        except KeyError:
            pass
        return "<%s owner=%r count=%d>" % (
                self.__class__.__name__, owner, self.__count)


    def acquire(self, blocking=1):
        """Acquire a lock, blocking or non-blocking.

        When invoked without arguments: if this thread already owns the lock,
        increment the recursion level by one, and return immediately. Otherwise,
        if another thread owns the lock, block until the lock is unlocked. Once
        the lock is unlocked (not owned by any thread), then grab ownership, set
        the recursion level to one, and return. If more than one thread is
        blocked waiting until the lock is unlocked, only one at a time will be
        able to grab ownership of the lock. There is no return value in this
        case.

        When invoked with the blocking argument set to true, do the same thing
        as when called without arguments, and return true.

        When invoked with the blocking argument set to false, do not block. If a
        call without an argument would block, return false immediately;
        otherwise, do the same thing as when called without arguments, and
        return true.

        """
        me = _get_ident()
        if self.__owner == me:
            self.__count = self.__count + 1
            if __debug__:
                self._note("%s.acquire(%s): recursive success", self, blocking)
            return 1
        rc = self.__block.acquire(blocking)
        if rc:
            self.__owner = me
            self.__count = 1
            if __debug__:
                self._note("%s.acquire(%s): initial success", self, blocking)
        else:
            if __debug__:
                self._note("%s.acquire(%s): failure", self, blocking)
        return rc

    __enter__ = acquire

    def release(self):
        """Release a lock, decrementing the recursion level.

        If after the decrement it is zero, reset the lock to unlocked (not owned
        by any thread), and if any other threads are blocked waiting for the
        lock to become unlocked, allow exactly one of them to proceed. If after
        the decrement the recursion level is still nonzero, the lock remains
        locked and owned by the calling thread.

        Only call this method when the calling thread owns the lock. A
        RuntimeError is raised if this method is called when the lock is
        unlocked.

        There is no return value.

        """
        if self.__owner != _get_ident():
            raise RuntimeError("cannot release un-acquired lock")
        self.__count = count = self.__count - 1
        if not count:
            self.__owner = None
            self.__block.release()
            if __debug__:
                self._note("%s.release(): final release", self)
        else:
            if __debug__:
                self._note("%s.release(): non-final release", self)

    def __exit__(self, t, v, tb):
        self.release()

    # Internal methods used by condition variables

    def _acquire_restore(self, count_owner):
        count, owner = count_owner
        self.__block.acquire()
        self.__count = count
        self.__owner = owner
        if __debug__:
            self._note("%s._acquire_restore()", self)

    def _release_save(self):
        if __debug__:
            self._note("%s._release_save()", self)
        count = self.__count
        self.__count = 0
        owner = self.__owner
        self.__owner = None
        self.__block.release()
        return (count, owner)

    def _is_owned(self):
        return self.__owner == _get_ident()
    
    
    
def Condition(*args, **kwargs):
    """Factory function that returns a new condition variable object.

    A condition variable allows one or more threads to wait until they are
    notified by another thread.

    If the lock argument is given and not None, it must be a Lock or RLock
    object, and it is used as the underlying lock. Otherwise, a new RLock object
    is created and used as the underlying lock.

    """
    return _Condition(*args, **kwargs)

class _Condition(_Verbose):
    """Condition variables allow one or more threads to wait until they are
       notified by another thread.
    """
    def __init__(self, lock=None, verbose=None):
        _Verbose.__init__(self, verbose)
        if lock is None:
            lock = RLock()
        self.__lock = lock
        # Export the lock's acquire() and release() methods
        self.acquire = lock.acquire
        self.release = lock.release
        # If the lock defines _release_save() and/or _acquire_restore(),
        # these override the default implementations (which just call
        # release() and acquire() on the lock).  Ditto for _is_owned().
        try:
            self._release_save = lock._release_save
        except AttributeError:
            pass
        try:
            self._acquire_restore = lock._acquire_restore
        except AttributeError:
            pass
        try:
            self._is_owned = lock._is_owned
        except AttributeError:
            pass
        self.__waiters = {}

    def __enter__(self):
        return self.__lock.__enter__()

    def __exit__(self, *args):
        return self.__lock.__exit__(*args)

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self.__lock, len(self.__waiters))

    def _release_save(self):
        self.__lock.release()           # No state to save

    def _acquire_restore(self, x):
        self.__lock.acquire()           # Ignore saved state

    def _is_owned(self):
        # Return True if lock is owned by current_thread.
        # This method is called only if __lock doesn't have _is_owned().
        if self.__lock.acquire(0):
            self.__lock.release()
            return False
        else:
            return True

    
    def wait(self, timeout=None):
        """Wait until notified or until a timeout occurs.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method releases the underlying lock, and then blocks until it is
        awakened by a notify() or notifyAll() call for the same condition
        variable in another thread, or until the optional timeout occurs. Once
        awakened or timed out, it re-acquires the lock and returns.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        When the underlying lock is an RLock, it is not released using its
        release() method, since this may not actually unlock the lock when it
        was acquired multiple times recursively. Instead, an internal interface
        of the RLock class is used, which really unlocks it even when it has
        been recursively acquired several times. Another internal interface is
        then used to restore the recursion level when the lock is reacquired.

        """
        t = threading.current_thread()
        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        waiter = _allocate_lock()
        
        waiter.acquire()
        if isinstance(t, InterruptableThread):
            t._InterruptableThread__lock.acquire()
            if t.interrupted: 
                t._InterruptableThread__lock.release()
                return
            t._waitingfor = self
        self.__waiters[t.ident] = waiter
        saved_state = self._release_save()
        try:    # restore state no matter what (e.g., KeyboardInterrupt)
            if timeout is None:
                if isinstance(t, InterruptableThread):
                    t._InterruptableThread__lock.release()
                waiter.acquire()
                if __debug__:
                    self._note("%s.wait(): got it", self)
            else:
                # Balancing act:  We can't afford a pure busy loop, so we
                # have to sleep; but if we sleep the whole timeout time,
                # we'll be unresponsive.  The scheme here sleeps very
                # little at first, longer as time goes on, but never longer
                # than 20 times per second (or the timeout time remaining).
                if isinstance(t, InterruptableThread):
                    t._InterruptableThread__lock.release()
                if __debug__:
                    self._note('%s.wait(%s): waiting for notification or timeout...', type(self).__name__, timeout)
                endtime = time.time() + timeout
                delay = 0.0005 # 500 us -> initial delay of 1 ms
                while True:
                    gotit = waiter.acquire(0)
                    if gotit:
                        break
                    remaining = endtime - time.time()
                    if remaining <= 0:
                        break
                    delay = min(delay * 2, remaining, .05)
                    time.sleep(delay)
                if not gotit:
                    if __debug__:
                        self._note("%s.wait(%s): timed out", type(self).__name__, timeout)
                    try:
                        del self.__waiters[t.ident]
                    except ValueError: pass
                else:
                    if __debug__:
                        self._note("%s.wait(%s): got it", self, timeout)
        finally:
            self._acquire_restore(saved_state)
        if isinstance(t, InterruptableThread):
            t.die_on_interrupt()
            

    def notify(self, n=1):
        """Wake up one or more threads waiting on this condition, if any.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method wakes up at most n of the threads waiting for the condition
        variable; it is a no-op if no threads are waiting.

        """
        if not self._is_owned():
            raise RuntimeError("cannot notify on un-acquired lock")
        __waiters = self.__waiters
        waiters = __waiters.keys()[:n]
        if not waiters:
            if __debug__:
                self._note("%s.notify(): no waiters", self)
            return
        self._note("%s.notify(): notifying %d waiter%s", self, n,
                   n!=1 and "s" or "")
        for waiter in waiters:
            __waiters[waiter].release()
            try:
                del __waiters[waiter]
            except KeyError:
                pass
    
    
    def notify_thread(self, tid):
        '''Wake up the thread with the given ID only, waiting on this condition.'''
        if not self._is_owned():
            raise RuntimeError("cannot notify on un-acquired lock")
        waiter = self.__waiters.get(tid)
        if waiter is None:
            if __debug__:
                self._note("%s.notify(): no thread with id %s waiting on condition", self, tid)
            return
        self._note("%s.notify(): notifying waiter of thread %s", self, tid)
        waiter.release()
        try:
            del self.__waiters[tid]
        except KeyError:
            pass


    def notifyAll(self):
        """Wake up all threads waiting on this condition.

        If the calling thread has not acquired the lock when this method
        is called, a RuntimeError is raised.

        """
        self.notify(len(self.__waiters))
        
    notify_all = notifyAll
        
def Semaphore(*args, **kwargs):
    """A factory function that returns a new semaphore.

    Semaphores manage a counter representing the number of release() calls minus
    the number of acquire() calls, plus an initial value. The acquire() method
    blocks if necessary until it can return without making the counter
    negative. If not given, value defaults to 1.

    """
    return _Semaphore(*args, **kwargs)


class _Semaphore(threading._Semaphore):
    """Semaphores manage a counter representing the number of release() calls
       minus the number of acquire() calls, plus an initial value. The acquire()
       method blocks if necessary until it can return without making the counter
       negative. If not given, value defaults to 1.

    """

    # After Tim Peters' semaphore class, but not quite the same (no maximum)

    def __init__(self, value=1, verbose=None):
        threading._Semaphore.__init__(self, value, verbose)
        self.__cond = Condition(Lock(verbose=1))
        self.__owners = set()


    def isowned(self):
        return threading.current_thread().ident in self.__owners
    

    def acquire(self, blocking=1):
        """Acquire a semaphore, decrementing the internal counter by one.

        When invoked without arguments: if the internal counter is larger than
        zero on entry, decrement it by one and return immediately. If it is zero
        on entry, block, waiting until some other thread has called release() to
        make it larger than zero. This is done with proper interlocking so that
        if multiple acquire() calls are blocked, release() will wake exactly one
        of them up. The implementation may pick one at random, so the order in
        which blocked threads are awakened should not be relied on. There is no
        return value in this case.

        When invoked with blocking set to true, do the same thing as when called
        without arguments, and return true.

        When invoked with blocking set to false, do not block. If a call without
        an argument would block, return false immediately; otherwise, do the
        same thing as when called without arguments, and return true.

        """
        rc = False
        with self.__cond:
            while self._Semaphore__value == 0:
                if not blocking:
                    break
                if __debug__:
                    self._note("%s.acquire(%s): blocked waiting, value=%s",
                            self, blocking, self._Semaphore__value)
                self.__cond.wait()
            else:
                self.__value = self._Semaphore__value - 1
                self.__owners.add(threading.current_thread().ident)
                if __debug__:
                    self._note("%s.acquire: success, value=%s", self, self._Semaphore__value)
                rc = True
        return rc

    __enter__ = acquire

    def release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When the counter is zero on entry and another thread is waiting for it
        to become larger than zero again, wake up that thread.

        """
        with self.__cond:
            self._Semaphore__value += 1
            if __debug__:
                self._note("%s.release: success, value=%s",
                        self, self._Semaphore__value)
            self.__owners.remove(threading.current_thread().ident)
            self.__cond.notify()

    def __exit__(self, t, v, tb):
        self.release()


def BoundedSemaphore(*args, **kwargs):
    """A factory function that returns a new bounded semaphore.

    A bounded semaphore checks to make sure its current value doesn't exceed its
    initial value. If it does, ValueError is raised. In most situations
    semaphores are used to guard resources with limited capacity.

    If the semaphore is released too many times it's a sign of a bug. If not
    given, value defaults to 1.

    Like regular semaphores, bounded semaphores manage a counter representing
    the number of release() calls minus the number of acquire() calls, plus an
    initial value. The acquire() method blocks if necessary until it can return
    without making the counter negative. If not given, value defaults to 1.

    """
    return _BoundedSemaphore(*args, **kwargs)


class _BoundedSemaphore(_Semaphore):
    """A bounded semaphore checks to make sure its current value doesn't exceed
       its initial value. If it does, ValueError is raised. In most situations
       semaphores are used to guard resources with limited capacity.
    """

    def __init__(self, value=1, verbose=None):
        _Semaphore.__init__(self, value, verbose)
        self._initial_value = value

    def release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When the counter is zero on entry and another thread is waiting for it
        to become larger than zero again, wake up that thread.

        If the number of releases exceeds the number of acquires,
        raise a ValueError.

        """
        with self._Semaphore__cond:
            if self._Semaphore__value >= self._initial_value:
                raise ValueError("Semaphore released too many times")
            self._Semaphore__value += 1
            self._Semaphore__cond.notify()


        

def Event(*args, **kwargs):
    """A factory function that returns a new event.

    Events manage a flag that can be set to true with the set() method and reset
    to false with the clear() method. The wait() method blocks until the flag is
    true.

    """
    return _Event(*args, **kwargs)

class _Event(threading._Event):
    """A factory function that returns a new event object. An event manages a
       flag that can be set to true with the set() method and reset to false
       with the clear() method. The wait() method blocks until the flag is true.

    """

    # After Tim Peters' event class (without is_posted())

    def __init__(self, verbose=None):
        threading._Event.__init__(self, verbose)
        self.__cond = Condition(Lock(), verbose=verbose)
        self.__flag = False

    def _reset_internal_locks(self):
        # private!  called by Thread._reset_internal_locks by _after_fork()
        self.__cond.__init__(Lock())

    def isSet(self):
        'Return true if and only if the internal flag is true.'
        return self.__flag

    is_set = isSet

    def set(self):
        """Set the internal flag to true.

        All threads waiting for the flag to become true are awakened. Threads
        that call wait() once the flag is true will not block at all.

        """
        with self.__cond:
            self.__flag = True
            self.__cond.notify_all()

    def clear(self):
        """Reset the internal flag to false.

        Subsequently, threads calling wait() will block until set() is called to
        set the internal flag to true again.

        """
        with self.__cond:
            self.__flag = False

    def wait(self, timeout=None):
        """Block until the internal flag is true.

        If the internal flag is true on entry, return immediately. Otherwise,
        block until another thread calls set() to set the flag to true, or until
        the optional timeout occurs.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        This method returns the internal flag on exit, so it will always return
        True except if a timeout is given and the operation times out.

        """
        with self.__cond:
            if not self.__flag:
                self.__cond.wait(timeout)
            return self.__flag        


def _async_raise(tid, exctype):
    '''Raises an exception in the threads with id tid'''
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    
    
def _revoke_exc(tid):
    '''Revokes a pending exception in the given thread.'''
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
    if res == 0:
        raise ValueError("invalid thread id")
    


class InterruptableThread(threading.Thread):
    '''A thread class that supports raising exception in the thread from
       another thread.
    '''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  args=args, kwargs=kwargs, verbose=verbose)
        self.__waitingfor = None 
        self.__running = Event()
        self.__lock = RLock()
        self.interrupted = False
        self.finished = False
        self.suspended = Event()
        self.resumed = Event()
        
        
    def setsuspended(self):
        self.resumed.clear()
        self.suspended.set()
        
    
    def setresumed(self):
        self.suspended.clear()
        self.resumed.set()
        
    
    def die_on_interrupt(self):
        '''If an interrupt has been signaled to this thread, waits in a busy 
        loop until the interpreter kills the thread by issuing the 
        ThreadInterrupt exception.
        
        If no interrupt is issued, this method immediately returns without 
        doing anything.
        '''
        with self.__lock:
            if self.interrupted: 
                if __debug__:
                    self._note('%s.die_on_interrupt(): waiting to die...', type(self).__name__)
                while 1: time.sleep(.001)
            
    
    @property
    def _waitingfor(self):
        return self.__waitingfor
    
    @_waitingfor.setter
    def _waitingfor(self, waiter):
        if self.interrupted and waiter is not None: raise RuntimeError()
        self.__waitingfor = waiter
        
    
    def __get_tid(self):
        """determines this (self's) thread id

        CAREFUL : this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.is_alive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        # TODO: in python 2.6, there's a simpler way to do : self.ident

        raise AssertionError("could not determine the thread's id")


    def __raise_exc(self, exctype):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raise_exc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raise_exc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL : this function is executed in the context of the
        caller thread, to raise an excpetion in the context of the
        thread represented by this instance.
        """
        _async_raise( self.__get_tid(), exctype )


    def kill(self):
        '''Raises an :class:`ThreadInterrupt` in this thread.'''
        if __debug__:
            self._note('%s._run(): sending ThreadInterrupt', self)
        self.__running.wait()
        if not self.is_alive(): return
        with self.__lock:
            if self.finished: return
            self.interrupted = True
            self.__raise_exc(ThreadInterrupt)
            if isinstance(self._waitingfor, _Condition):
                with self._waitingfor, _active_limbo_lock:
                    self._waitingfor.notify_thread(self.__get_tid())
                    self._waitingfor = None
        self.join()
                
                
    def undo_kill(self):
        '''Revokes a pending exception in the given thread.
        
        Note: this does not seem to work reliably. Better not use.'''
        if __debug__:
            self._note('%s.undo_kill()', self)
        _revoke_exc(self.__get_tid())
        
    
    def _run(self):
        try:
            self.__running.set()
            try:
                self.run()
            except ThreadInterrupt as e:
                if __debug__:
                    self._note('%s._run(): received ThreadInterrupt', self)
                sys.stdout.flush()
                raise e
            else:
                with self.__lock:
                    self.finished = True
                    # if a ThreadInterrupt exception has been sent to
                    # this thread, we have to wait until the interpreter 
                    # actually fires it. This is because it cannot be revoked 
                    # reliably. The thread has to busily wait until it dies. 
                    self.die_on_interrupt()
        except (SystemExit, KeyboardInterrupt, ThreadInterrupt), e: 
            if __debug__:
                self._note("%s._run(): %s", self, type(e).__name__)
        except Exception as e:
            traceback.print_exc()
            if __debug__:
                self._note("%s._run(): calling %s._except(%s)", self, self, type(e).__name__)
            self._except(e)
        else:
            if __debug__:
                self._note("%s._run(): calling %s._else()", self, self)
            self._else()
        finally:
            if __debug__:
                self._note("%s._run(): calling %s._finally()", self, self)
            self._finally()
            

    def _except(self, e):
        if __debug__:
            self._note("%s._except(): re-raising exception", self) 
        raise e
    
    def _finally(self): pass
    
    def _else(self): pass

    def _Thread__bootstrap_inner(self):
        try:
            self._set_ident()
            self._Thread__started.set()
            with _active_limbo_lock:
                _active[self._Thread__ident] = self
                del _limbo[self]
            if __debug__:
                self._note("%s.__bootstrap(): thread started", self)

            if _trace_hook:
                self._note("%s.__bootstrap(): registering trace hook", self)
                sys.settrace(_trace_hook)
            if _profile_hook:
                self._note("%s.__bootstrap(): registering profile hook", self)
                sys.setprofile(_profile_hook)

            try:
                self._run()
            except SystemExit as e:
                if __debug__:
                    self._note("%s.__bootstrap(): raised SystemExit", self)
            except ThreadInterrupt:
                if sys and sys.stderr is not None:
                    print>>sys.stderr, ("Interrupt in thread %s: !!! THIS SHOULD NEVER HAPPEN !!!\n%s" %
                                         (self.name, traceback.format_exc()))
                
            except Exception:
                if __debug__:
                    self._note("%s.__bootstrap(): unhandled exception", self)
                # If sys.stderr is no more (most likely from interpreter
                # shutdown) use self.__stderr.  Otherwise still use sys (as in
                # _sys) in case sys.stderr was redefined since the creation of
                # self.
                if sys and sys.stderr is not None:
                    print>>sys.stderr, ("Exception in thread %s:\n%s" %
                                         (self.name, traceback.format_exc()))
                elif self._Thread__stderr is not None:
                    # Do the best job possible w/o a huge amt. of code to
                    # approximate a traceback (code ideas from
                    # Lib/traceback.py)
                    exc_type, exc_value, exc_tb = self._Thread__exc_info()
                    try:
                        print>>self._Thread__stderr, (
                            "Exception in thread " + self.name +
                            " (most likely raised during interpreter shutdown):")
                        print>>self._Thread__stderr, (
                            "Traceback (most recent call last):")
                        while exc_tb:
                            print>>self._Thread__stderr, (
                                '  File "%s", line %s, in %s' %
                                (exc_tb.tb_frame.f_code.co_filename,
                                    exc_tb.tb_lineno,
                                    exc_tb.tb_frame.f_code.co_name))
                            exc_tb = exc_tb.tb_next
                        print>>self._Thread__stderr, ("%s: %s" % (exc_type, exc_value))
                    # Make sure that exc_tb gets deleted since it is a memory
                    # hog; deleting everything else is just for thoroughness
                    finally:
                        del exc_type, exc_value, exc_tb
            else:
                if __debug__:
                    self._note("%s.__bootstrap(): normal return", self)
            finally:
                # Prevent a race in
                # test_threading.test_no_refcycle_through_target when
                # the exception keeps the target alive past when we
                # assert that it's dead.
                self._Thread__exc_clear()
        finally:
            with _active_limbo_lock:
                self._Thread__stop()
                self.setsuspended()
                try:
                    # We don't call self.__delete() because it also
                    # grabs _active_limbo_lock.
                    del _active[_get_ident()]
                except:
                    pass
                
                
    def start(self):
        """Start the thread's activity.

        It must be called at most once per thread object. It arranges for the
        object's run() method to be invoked in a separate thread of control.

        This method will raise a RuntimeError if called more than once on the
        same thread object.

        """
        if not self._Thread__initialized:
            raise RuntimeError("thread.__init__() not called")
        if self._Thread__started.is_set():
            raise RuntimeError("threads can only be started once")
        if __debug__:
            self._note("%s.start(): starting thread", self)
        with _active_limbo_lock:
            _limbo[self] = self
        try:
            _start_new_thread(self._Thread__bootstrap, ())
        except Exception:
            with _active_limbo_lock:
                del _limbo[self]
            raise
        self._Thread__started.wait()
        return self


class SessionThread(InterruptableThread):
    '''
    An interruptable thread class that inherits the session information
    from the parent thread.
    '''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        InterruptableThread.__init__(self, target=target, name=name,
                 args=args, kwargs=kwargs, verbose=verbose)
        self._session = pyrap.session
        self._session_id = pyrap.session.session_id

    def _run(self):
        pyrap.session.session_id = self._session_id
        pyrap.session.load()
        if __debug__:
            self._note('%s._run(): inherited data from session %s', self, pyrap.session.session_id)
        InterruptableThread._run(self)


if __name__ == '__main__':
    s = Semaphore(value=1, verbose=1)
    
    class IThread(InterruptableThread):
        
        def run(self):
            sleep(random.random())
            out(threading.current_thread(), 'trying to acquire semaphore')
            s.acquire()
            out(threading.current_thread(), 'has semaphore') 
            sleep(random.random() * 5)
        
        def _finally(self):
            if s.isowned():
                out(threading.current_thread(), 'releasing')
                s.release()
                out(threading.current_thread(), 'released')
        
    thrs = []
    for i in range(1):
        out('Iter #%s' % (i+1))
        t = IThread(verbose=1)
        thrs.append(t)
        t.start()
    for t in thrs:
#         out('killing', t)
#         t.kill()
        t.join()
    out('goodbye')
    

