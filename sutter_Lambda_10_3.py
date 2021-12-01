import serial

class Controller:
    '''
    Basic device adaptor for Sutter Lambda 10-3 pptical filter changer and
    SmartShutter® control system. Many more commands are available and have
    not been implemented.
    - Note: to enable serial communicaion use the front of the controller to
    set the default communications port = serial (press: MODE 7 1 4 2)
    '''
    def __init__(self, which_port, verbose=True):
        self.verbose = verbose
        if self.verbose: print(
            'Initializing Lambda_10_3 with "Wheel A" = 10 position 25mm...',
            end='')
        try:
            self.port = serial.Serial(port=which_port, timeout=5)
        except serial.serialutil.SerialException:
            raise IOError('Unable to connect to Lambda_10_3 on %s'%which_port)
        self.port.write(b'\xFD') # get controller type and configuration
        response = self.port.readline()
        if response != b'\xfd10-3WA-25WB-NCWC-NCSA-VSSB-VS\r':
            print('Controller response =', response)
            raise IOError("We don't yet support this Lambda_10_3 configuration")
        if self.verbose: print('done.')
        self._pending_cmd = None
        self.move(0) # use as shutter

    def move(self, position, wheel=0, speed=6, block=True): # speed=6 = reliable
        if self._pending_cmd is not None:
            self._finish_moving()
        assert position in range(10)
        assert speed in range(8)
        assert wheel == 0
        if self.verbose:
            print('Moving filter wheel %i to position %i with speed %i... '%(
                wheel, position, speed), end='')
        cmd = bytes([(wheel << 7) + (speed << 4) + position])
        self.port.write(cmd)
        self._pending_cmd = cmd
        if block:
            self._finish_moving()
        else: print('\r')
        return None

    def _finish_moving(self):
        if self._pending_cmd is None:
            return
        response = self.port.read(2)
        if response != self._pending_cmd + b'\r':
            print('Controller response =', response)
            raise IOError('Unexpected response from Lambda_10_3')
        assert self.port.in_waiting == 0
        self.position = self._pending_cmd[0] & 0b00001111
        self._pending_cmd = None
        if self.verbose: print('done.')
        return None

    def close(self):
        self.move(0) # use as shutter
        self.port.close()
        if self.verbose: print('Closed Lambda_10_3 COM port.')
        return None

if __name__ == '__main__':
    import time
    import random
    filter_wheel = Controller(which_port='COM5')

    # performance tests:
    print('\n#Filter wheel position = ', filter_wheel.position)

    print('\n# Adjacent (fastest) move:')
    start = time.perf_counter()
    filter_wheel.move(1)
    print('(time: %0.4fs)'%(time.perf_counter() - start))

    print('\n# Opposite (slowest) move:')
    start = time.perf_counter()
    filter_wheel.move(6)
    print('(time: %0.4fs)'%(time.perf_counter() - start))    

    print('\n# Non blocking call:')
    start = time.perf_counter()
    filter_wheel.move(0, block=False)
    print('(time: %0.4fs)'%(time.perf_counter() - start))
    print('(do something else...)')
    print('# Finish call:')
    filter_wheel._finish_moving()
    print('(time: %0.4fs, including prints)\n'%(time.perf_counter() - start))

##    # reliability tests:
##    moves = 100
##    for i in range(moves):
##        position = i%10
##        filter_wheel.move(position)
##    for i in range(moves):
##        position = random.randint(0, 9)
##        filter_wheel.move(position)
##
##    filter_wheel.verbose = False
##    for i in range(moves):
##        position = i%10
##        filter_wheel.move(position)
##    for i in range(moves):
##        position = random.randint(0, 9)
##        filter_wheel.move(position)

    filter_wheel.close()
