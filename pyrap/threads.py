import threading
# from pyrap import session
import pyrap
import ctypes
import inspect
import time
from pyrap.utils import out
from threading import _active_limbo_lock, _active, _limbo,\
    _trace_hook, _profile_hook, _get_ident, Lock, _allocate_lock, RLock
import sys
import traceback
import random


class ThreadInterrupt(Exception): pass

from threading import enumerate  # @UnusedImport


def sleep(sec):
    '''Interruptable sleep'''
    ev = Event(verbose=0)
    ev.wait(sec)
    
    
def Condition(*args, **kwargs):
    """Factory function that returns a new condition variable object.

    A condition variable allows one or more threads to wait until they are
    notified by another thread.

    If the lock argument is given and not None, it must be a Lock or RLock
    object, and it is used as the underlying lock. Otherwise, a new RLock object
    is created and used as the underlying lock.

    """
    return _Condition(*args, **kwargs)

class _Condition(threading._Condition):
    """Condition variables allow one or more threads to wait until they are
       notified by another thread.
    """

    def __init__(self, lock=None, verbose=None):
        threading._Condition.__init__(self, lock, verbose)
        self.__waiters = {}

    
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
                        self._note("%s.wait(%s): timed out", self, timeout)
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
            

    def __enter__(self):
        return self._Condition__lock.__enter__()

    def __exit__(self, *args):
        if self._is_owned():
            return self._Condition__lock.__exit__(*args)
    

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
                    self._note('%s.die_on_interrupt(): waiting to die...' % self)
                while 1: time.sleep(.00001)
            
    
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
        self.__running.wait()
        if not self.is_alive(): return
        with self.__lock:
            if self.finished: return
            self.interrupted = True
            self.__raise_exc(ThreadInterrupt)
            if isinstance(self._waitingfor, _Condition):
                with self._waitingfor:
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
                    print>>sys.stderr, ("Caught Exception in thread %s:\n%s" %
                                         (self.name, traceback.format_exc()))
                elif self._Thread__stderr is not None:
                    # Do the best job possible w/o a huge amt. of code to
                    # approximate a traceback (code ideas from
                    # Lib/traceback.py)
                    exc_type, exc_value, exc_tb = self._Thread__exc_info()
                    try:
                        print>>self._Thread__stderr, (
                            "Caught Exception in thread " + self.name +
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
                try:
                    # We don't call self.__delete() because it also
                    # grabs _active_limbo_lock.
                    del _active[_get_ident()]
                except:
                    pass


class UIThread(InterruptableThread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        InterruptableThread.__init__(self)
        self._session = pyrap.session
        self._session_id = pyrap.session.session_id

    def run(self):
        pyrap.session.session_id = self._session_id
        pyrap.session.load()
        self._run()
        
    def _run(self): pass


if __name__ == '__main__':
    for i in range(100):
        out('Iter #%s' % (i+1))
        cond = Condition(verbose=0)
        event = Event(verbose=0)
        def worker():
#             print(i+1, 'working...')
#             sleep(random.random() * 10)
#             out(threading.current_thread().interrupted)
            sleep(random.random())
#             out('sleep finished')
            with cond:
                cond.wait(random.random())
#             out(threading.current_thread().interrupted)
#             print 'waiting for event'
            sleep(random.random() * 5)
#             out('thread returns')
#             event.wait()
        t = InterruptableThread(target=worker, verbose=0)
        waiting = random.random()
        start = time.time()
        t.start()
        time.sleep(waiting)
        t.kill()
        t.join()
        end = time.time()
        out('total: %s sec, wait: %s sec, kill: %s sec' % (end-start, waiting, end-start-waiting))
        sys.stdout.flush()
#         out(i+1, 'notifying and sleeping')
    #     time.sleep(5)
#         out('goodbye.')
#     with cond:
#         cond.notify_all()
    
    
    
    

