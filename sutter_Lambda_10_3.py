import serial

class Controller:
    '''
    Basic device adaptor for Sutter Lambda 10-3 pptical filter changer and
    SmartShutter® control system. Many more commands are available and have
    not been implemented.
    - Note: to enable serial communication use the front of the controller to
    set the default port to 'S' (press: LOCAL -> MODE -> 7 1 4 2 0 + restart)
    '''
    def __init__(self,
                 which_port,
                 wheel_A='LB10-NWE',
                 wheel_B=None,
                 name='Lambda 10-3',
                 verbose=True):
        self.name = name
        self.verbose = verbose
        if self.verbose:
            print('%s: opening with wheel_A = %s and wheel_B = %s '%(
                self.name, wheel_A, wheel_B))
        try:
            self.port = serial.Serial(port=which_port, timeout=1)
        except serial.serialutil.SerialException:
            raise IOError('%s: unable to connect on %s'%(
                self.name, which_port))
        self.port.write(b'\xFD') # get controller type and configuration
        configuration = self.port.read_until(b'\r')
        if self.verbose:
            print('%s: configuration = %s'%(self.name, configuration))
        if wheel_A == 'LB10-NWE' and wheel_B == None:
            assert configuration == b'\xfd10-3WA-25WB-NCWC-NCSA-VSSB-VS\r',(
                "%s: configuration not supported"%self.name)
            self.wheels =       (0,)
            self.position_max = (10,)
            self.position =     [None]
            self._pending_cmd = [None]
            self.move(0) # use as shutter
        if wheel_A == 'LB10-NWE' and wheel_B == 'LB10-NWE':
            assert configuration == b'\xfd10-3WA-25WB-25WC-NCSA-VSSB-VS\r',(
                "%s: configuration not supported"%self.name)
            self.wheels =       (0, 1)
            self.position_max = (10, 10)
            self._pending_cmd = [None, None]
            self.position =     [None, None]
            for wheel in self.wheels:
                self.move(0, wheel=wheel) # use as shutter
        if self.verbose: print('%s: done opening'%self.name)

    def move(self, position, wheel=0, speed=6, block=True): # speed=6 = reliable
        assert wheel in self.wheels
        if self._pending_cmd[wheel] is not None:
            self._finish_moving()
        assert position in range(self.position_max[wheel])
        assert speed in range(8)
        if self.verbose:
            print('%s: moving wheel %i to position %i (speed=%i)'%(
                self.name, wheel, position, speed))
        cmd = bytes([(wheel << 7) + (speed << 4) + position])
        self.port.write(cmd)
        self._pending_cmd[wheel] = cmd
        if block:
            self._finish_moving()
        return None

    def _finish_moving(self):
        if all(cmd is None for cmd in self._pending_cmd):
            return
        response = self.port.read(2)
        # check which wheel the response corresonds to:
        wheel = None
        crash = True
        for w in self.wheels:
            if self._pending_cmd[w] is not None:
                if response == self._pending_cmd[w] + b'\r':
                    wheel = w
                    crash = False
                    break
        if crash: # the response does not match a _pending_cmd
            print('%s: response =', response)
            raise IOError('%s: unexpected response'%self.name)
        self.position[wheel] = self._pending_cmd[wheel][0] & 0b00001111
        self._pending_cmd[wheel] = None
        if all(cmd is None for cmd in self._pending_cmd):
            assert self.port.in_waiting == 0
        if self.verbose: print('%s: -> finished moving.'%self.name)
        return None

    def close(self):
        for wheel in self.wheels:
            self.move(0, wheel=wheel) # use as shutter
        self.port.close()
        if self.verbose: print('%s: closed.'%self.name)
        return None

if __name__ == '__main__':
    import time
    import random

    # test 1 wheel (1x LB10-NWE):
    filter_wheel = Controller(
        which_port='COM9', wheel_A='LB10-NWE', verbose=True)

##    # test 2 wheels (2x LB10-NWE):
##    filter_wheel = Controller(
##        which_port='COM9', wheel_A='LB10-NWE', wheel_B='LB10-NWE', verbose=True)

    # performance tests:
    for wheel in filter_wheel.wheels:
        print('\n#Filter wheel %i position = %i'%(
            wheel, filter_wheel.position[wheel]))

    print('\n# Adjacent (fastest) move:')
    for wheel in filter_wheel.wheels:
        t0 = time.perf_counter()
        filter_wheel.move(1, wheel=wheel)
        print('(time: %0.4fs)'%(time.perf_counter() - t0))

    print('\n# Opposite (slowest) move:')
    for wheel in filter_wheel.wheels:
        t0 = time.perf_counter()
        filter_wheel.move(6, wheel=wheel)
        print('(time: %0.4fs)'%(time.perf_counter() - t0))    

    print('\n# Non blocking call:')
    for wheel in filter_wheel.wheels:
        t0 = time.perf_counter()
        filter_wheel.move(0, wheel=wheel, block=False)
        print('(time: %0.4fs)'%(time.perf_counter() - t0))
        print('(do something else...)')
        print('# Finish call:')
        filter_wheel._finish_moving()
        print('(time: %0.4fs, including prints)\n'%(time.perf_counter() - t0))

##    print('\n# Non blocking call with 2 wheels:')
##    for i in range(10):
##        t0 = time.perf_counter()
##        filter_wheel.move(6, wheel=0, block=False) # move to 6 is slower...
##        filter_wheel.move(1, wheel=1, block=False)
##        print('(time: %0.4fs)'%(time.perf_counter() - t0))
##        print('(do something else...)')
##        print('# Finish call:')
##        filter_wheel._finish_moving()
##        filter_wheel._finish_moving()
##        print('(time: %0.4fs, including prints)\n'%(time.perf_counter() - t0))
##        for wheel in filter_wheel.wheels:
##            filter_wheel.move(0, wheel=wheel) # reset

##    # reliability tests:
##    moves = 100
##    for wheel in filter_wheel.wheels:
##        filter_wheel.verbose = True
##        for i in range(moves):
##            position = i%10
##            filter_wheel.move(position, wheel=wheel)
##        for i in range(moves):
##            position = random.randint(0, 9)
##            filter_wheel.move(position, wheel=wheel)
##
##        filter_wheel.verbose = False
##        for i in range(moves):
##            position = i%10
##            filter_wheel.move(position, wheel=wheel)
##        for i in range(moves):
##            position = random.randint(0, 9)
##            filter_wheel.move(position, wheel=wheel)

    filter_wheel.close()
