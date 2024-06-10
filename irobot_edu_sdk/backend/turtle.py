#
# Licensed under 3-Clause BSD license available in the License file. Copyright (c) 2023 iRobot Corporation. All rights reserved.
#

"""
This is a Turtle class that implements the Backend interface methods. It is very much incomplete and should be considered in ALPHA.

It is compatible with any Python installation which also supports the Python Turtle graphics class.
"""

from asyncio import sleep, Lock
from queue import SimpleQueue
from .backend import Backend
from ..packet import Packet

import random
import string
import turtle
from struct import pack, unpack


class Turtle(Backend):
    DIST_SCALE = 10

    def __init__(self, name: str = None):
        """If no name is provided, one will be autogenerated."""
        if name is not None:
            self._name = name
        else:
            self._name = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))

        self._txlock = Lock()
        self._queue: SimpleQueue = SimpleQueue()
        self._connected = False
        print("WARNING: THE TURTLEBACKEND DOESN'T SUPPORT MOST COMMANDS AND IS IN ALPHA!!")

    async def connect(self):
        """This method does not exit until a robot is found"""

        turtle.clearscreen()
        turtle.speed('slow')
        turtle.up()
        turtle.setx(0)
        turtle.sety(0)
        turtle.seth(90)
        turtle.colormode(255)
        turtle.shape('turtle')
        self._connected = True

    async def is_connected(self) -> bool:
        return self._connected

    async def disconnect(self):
        self._connected = False

    async def read_packet(self) -> Packet:
        while self._queue.empty():
            await sleep(0)
        return self._queue.get()

    async def write_packet(self, packet: Packet):
        if self._connected:
            async with self._txlock:
                #print(packet)
                if packet.dev == 0: # General
                    if packet.cmd == 3:
                        turtle.home()
                        turtle.seth(90)
                    else:
                        print("Unsupported general command", packet.cmd)

                elif packet.dev == 1: # Motors
                    send_motor_response = False
                    if packet.cmd == 8: # Drive distance
                        distance = unpack('>i', packet.payload[0:4])[0] / 10
                        turtle.forward(distance * self.DIST_SCALE)
                        send_motor_response = True
                    elif packet.cmd == 12: # Drive Angle
                        angle = unpack('>i', packet.payload[0:4])[0] / 10
                        turtle.right(angle)
                        send_motor_response = True
                    elif packet.cmd == 15: # Reset Position
                        turtle.setx(0)
                        turtle.sety(0)
                        turtle.seth(90)
                    elif packet.cmd == 17: # Navigate to Position
                        x = unpack('>i', packet.payload[0:4])[0] / 10
                        y = unpack('>i', packet.payload[4:8])[0] / 10
                        h = unpack('>i', packet.payload[8:12])[0] / 10
                        turtle.left(turtle.towards(x, y))
                        turtle.goto(x, y)
                        if h >= 0:
                            turtle.seth(h)
                        send_motor_response = True
                    elif packet.cmd == 27: # Drive Arc
                        angle = unpack('>i', packet.payload[0:4])[0] / 10
                        radius = unpack('>i', packet.payload[4:8])[0] / 10
                        turtle.circle(-radius * self.DIST_SCALE, angle if radius > 0 else -angle)
                        send_motor_response = True
                    else:
                        print("Unsupported motor command", packet.cmd)
                    if send_motor_response:
                        #TODO: Calulate robot pose internally instead of using world pose in order to more realistically model bias and offset
                        self._queue.put(Packet(packet.dev, packet.cmd, packet.inc, pack('>iiih', 0, int(turtle.xcor()*10/self.DIST_SCALE), int(turtle.ycor()*10/self.DIST_SCALE), int(turtle.heading()*10)), force_crc=True))

                elif packet.dev == 2: # Marker / Eraser
                    if packet.cmd == 0:
                        if packet.payload[0] == 0: # Everything up
                            turtle.up()
                        elif packet.payload[0] == 1: # Pen Down
                            turtle.down()
                        elif packet.payload[0] == 2: # Eraser Down
                            print("Erase (unsupported)")
                            turtle.up()
                            # TODO: improve eraser
                        else:
                                print("Unexpected marker/eraser position", packet.payload[0])
                        self._queue.put(Packet(packet.dev, packet.cmd, packet.inc, packet.payload, force_crc=True))
                    else:
                        print("Unexpected marker/eraser command", packet.cmd)

                elif packet.dev == 3: # LED Lights
                    if packet.cmd == 2: # Set LED Animation
                        if packet.payload[0] != 0: # treat all non-"off" commands as "on"
                            turtle.fillcolor(packet.payload[1], packet.payload[2], packet.payload[3])
                        else:
                            turtle.fillcolor(0, 0, 0)
                    else:
                        print("Unexpected LED Lights command", packet.cmd)

                else:
                        print("Unhandled device", packet.dev)