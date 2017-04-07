import time

from enum import IntEnum
from i2c import I2C


class Command(IntEnum):
    Forward = 1
    Backward = 2
    TurnLeft = 3
    TurnRight = 4
    SetSpeed = 5
    Stop = 6
    GetDistanceDone = 7
    IsDone = 8
    IsStopped = 9
    Resume = 10


class Motors(I2C):
    def __init__(self, address):
        super(Motors, self).__init__(address)

    def set_path(self, path, callback):
        for action in path:
            val = action['value']
            if action['action'] == 'move':
                if val > 0:
                    self.forward(val)
                else:
                    self.backward(val)
            elif action['action'] == 'turn':
                if val > 0:
                    self.turn_right(val)
                else:
                    self.turn_left(val)

            # Wait before action is done.
            while not self.is_done():
                time.sleep(0.1)
                callback()

    def forward(self, distance):
        self.send([Command.Forward, distance])

    def backward(self, distance):
        self.send([Command.Backward, distance])

    def turn_left(self, angle):
        self.send([Command.TurnLeft, angle])

    def turn_right(self, angle):
        self.send([Command.TurnRight, angle])

    def set_speed(self, speed):
        self.send([Command.SetSpeed, speed])

    def stop(self):
        self.send(Command.Stop)

    def distance_travelled(self):
        self.send(Command.DistanceTravelled)
        r = self.receive(2)
        return {
            "left": r[0],
            "right": r[1]
        }

    def is_done(self):
        self.send(Command.IsDone)
        return self.receive()

    def is_stopped(self):
        self.send(Command.IsStopped)
        return self.receive()

    def resume(self):
        self.send(Command.Resume)
