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
    for tid, tobj in threading._active.items():
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

def ILock(verbose=None):
    return _ILock(verbose=verbose)


class _ILock(_Verbose):
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

    def __exit__(self, e, t, tb):
#         if t is ThreadInterrupt: raise e
        self.__lock.__exit__(e, t, tb)

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
        t = thisthread()
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
            t.setsuspended()
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
            if isinstance(t, InterruptableThread) and t._InterruptableThread__interrupt:
                raise ThreadInterrupt()
            

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
        waiters = list(__waiters.keys())[:n]
        if not waiters:
            if __debug__:
                self._note("%s.notify(): no waiters", self)
            return
        self._note("%s.notify(): notifying %d waiter%s", self, n,
                   n!=1 and "s" or "")
        for waiter in waiters:
            t = active().get(waiter)
            if isinstance(t, InterruptableThread): 
                t.setresumed()
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
        t = active().get(tid)
        if isinstance(t, InterruptableThread): 
            t.setresumed()
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
        self.__cond = Condition(Lock())
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
            try:
                self.__owners.remove(threading.current_thread().ident)
            except KeyError: pass
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


class Kapo(_Verbose):
    '''
    More complex synchronization data structure implementing a Kapo (german 'foreman').
    
    A kapo can be used in a thread to wait until a number of tasks have been accomplished.
    The thread holding the kapo, however, does not work any of the tasks itself, but it
    just waits until all tasks have been done by other threads. Only one thread can hold
    the kapo at a time.
    '''
    def __init__(self, tasks=0, verbose=None):
        _Verbose.__init__(self, verbose)
        self.__mutex = Semaphore(value=1)
        self.__lock = RLock()
        self.__tasks = 0
        self.__done = Event()

    def _checkowner(self):
        if not self.__mutex._Semaphore__owners:
            raise RuntimeError('Kapo must be owned by a thread.')


    def acquire(self):
        with self.__lock:
            self.__mutex.acquire()

        
    def release(self):
        with self.__lock:
            self.__mutex.release()

        
    def __enter__(self):
        with self.__lock:
            self.acquire()
            self.reset()

        
    def __exit__(self, e, t, tb):
        self.release()


    def wait(self):
        if _get_ident() not in self.__mutex._Semaphore__owners:
            raise RuntimeError('a thread must have acquired the kapo in order to wait for it.')
        if __debug__:
            self._note('%s.wait(): thread %s is waiting with kapo until all jobs are done.' % (self, thisthread()))
        self.__done.wait()


    def reset(self):
        self._checkowner()
        with self.__lock:
            self.__tasks = 0
            self.__done.clear()

        
    def inc(self):
        '''Increments the counter of tasks to accomplish.'''
        self._checkowner()
        with self.__lock:
            self.__tasks += 1
            if __debug__:
                self._note('%s.inc(): new value is %s' % (self, self.__tasks))


    def dec(self):
        '''Decrements the counter of tasks to accomplish. 
        
        Notifies the thread holding the kapo and waiting for the completio tasks 
        when the counter reaches 0.'''
        self._checkowner()
        with self.__lock:
            self.__tasks -= 1
            if self.__tasks == 0:
                if __debug__:
                    self._note('%s.inc(): all jobs done. notifying kapo.' % self)
                self.__done.set()
            else:
                if __debug__:
                    self._note('%s.dec(): new value is %s' % (self, self.__tasks))


class InterruptableThread(threading.Thread):
    '''A thread class that supports interruption of blocking waits from within
       another thread.
    '''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  args=args, kwargs=kwargs, verbose=verbose)
        self.__waitingfor = None 
        self.__running = Event()
        self.__lock = RLock()
        self.__interrupt = False
        self.finished = False
        self.suspended = Event()
        self.resumed = Event()
        
        
    def setsuspended(self):
        self.resumed.clear()
        self.suspended.set()
        
    
    def setresumed(self):
        self.suspended.clear()
        self.resumed.set()
    
    
    def setdone(self):
        self.resumed.clear()
        self.suspended.set()
        
    
    @property
    def _waitingfor(self):
        return self.__waitingfor
    
    @_waitingfor.setter
    def _waitingfor(self, waiter):
        if self.__interrupt and waiter is not None: raise RuntimeError()
        self.__waitingfor = waiter
        
    @property
    def interrupted(self):
        return self.__interrupt
        
    def interrupt(self):
        with self.__lock:
            self.__interrupt = True
            if isinstance(self.__waitingfor, _Condition):
                with self.__waitingfor:
                    self._waitingfor.notify_thread(self.ident)
                

    def _run(self):
        self.run()


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
                    print("Interrupt in thread {}:\n{}".format(self.name, traceback.format_exc()), file=sys.stderr)
                
            except Exception:
                if __debug__:
                    self._note("%s.__bootstrap(): unhandled exception", self)
                # If sys.stderr is no more (most likely from interpreter
                # shutdown) use self.__stderr.  Otherwise still use sys (as in
                # _sys) in case sys.stderr was redefined since the creation of
                # self.
                if sys and sys.stderr is not None:
                    print(("Exception in thread %s:\n%s" %
                                         (self.name, traceback.format_exc())), file=sys.stderr)
                elif self._Thread__stderr is not None:
                    # Do the best job possible w/o a huge amt. of code to
                    # approximate a traceback (code ideas from
                    # Lib/traceback.py)
                    exc_type, exc_value, exc_tb = self._Thread__exc_info()
                    try:
                        print((
                            "Exception in thread " + self.name +
                            " (most likely raised during interpreter shutdown):"), file=self._Thread__stderr)
                        print((
                            "Traceback (most recent call last):"), file=self._Thread__stderr)
                        while exc_tb:
                            print((
                                '  File "%s", line %s, in %s' %
                                (exc_tb.tb_frame.f_code.co_filename,
                                    exc_tb.tb_lineno,
                                    exc_tb.tb_frame.f_code.co_name)), file=self._Thread__stderr)
                            exc_tb = exc_tb.tb_next
                        print(("%s: %s" % (exc_type, exc_value)), file=self._Thread__stderr)
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
                self.setdone()
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


class DetachedSessionThread(InterruptableThread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        InterruptableThread.__init__(self, target=target, name=name,
                 args=args, kwargs=kwargs, verbose=verbose)
        self._session = pyrap.session
        self._session_id = pyrap.session.session_id
    
    def _run(self):
        self.__sessionload()
        InterruptableThread._run(self)
    
    def __sessionload(self):
        pyrap.session.session_id = self._session_id
        pyrap.session.load()
        if __debug__:
            self._note('%s._run(): inherited data from session %s', self, pyrap.session.session_id)
        

class SessionThread(DetachedSessionThread):
    '''
    An interruptable thread class that inherits the session information
    from the parent thread.
    '''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        DetachedSessionThread.__init__(self, target=target, name=name,
                 args=args, kwargs=kwargs, verbose=verbose)
        self.__detached = False
        self.__exception = None

    def setsuspended(self):
        InterruptableThread.setsuspended(self)
        if not self.__detached:
            pyrap.session.runtime.kapo.dec()

    def setresumed(self):
        if not self.__detached: 
            pyrap.session.runtime.kapo.inc()
        InterruptableThread.setresumed(self)

    def setfinished(self):
        InterruptableThread.setsuspended(self)

    def _run(self):
        self._DetachedSessionThread__sessionload()
        try:
            InterruptableThread._run(self)
        except Exception as e:
            self.__exception = e
            traceback.print_exc()
            raise e
        finally:
            if not self.__detached:
                pyrap.session.runtime.kapo.dec()

            
    def start(self):
        self.setresumed()
        return InterruptableThread.start(self)
    
    def detach(self):
        with self._InterruptableThread__lock:
            if self.__detached:
                raise RuntimeError('Thread is already detached from session.')
            pyrap.session.runtime.kapo.dec()
            self.__detached = True
            
        


if __name__ == '__main__':
    s = Semaphore(value=1, verbose=1)
    c = Condition()
    kapo = Kapo(verbose=1)
    
    def worker():
        kapo.inc()
        sleep(random.random())
#         out(threading.current_thread(), 'trying to acquire semaphore')
#         with s:
#             out(threading.current_thread(), 'has semaphore') 
#             sleep(random.random() * 2)
        kapo.dec()
        
    thrs = []
    
    with kapo:
        for i in range(10):
            out('Iter #%s' % (i+1))
            t = InterruptableThread(target=worker, verbose=0)
            thrs.append(t)
            t.start()
        kapo.wait()

#     for t in thrs:
#         out('killing', t)
#         t.interrupt()
#         t.join()
    out('goodbye')
    

