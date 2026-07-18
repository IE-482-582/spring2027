#!/usr/bin/env python3

import argparse
import math
import time

from gz.transport13 import Node
from gz.msgs10.twist_pb2 import Twist


parser = argparse.ArgumentParser()
parser.add_argument("--model", default="car1", help="Model name (default: car1)")
args = parser.parse_args()

node = Node()

cmd_pub = node.advertise(
    f"/model/{args.model}/cmd_vel",
    Twist,
)

# Allow gz-transport time to discover the subscriber before sending messages.
time.sleep(0.5)


def set_command(linear_m_s: float, angular_rad_s: float) -> None:
    msg = Twist()
    msg.linear.x = linear_m_s
    msg.angular.z = angular_rad_s
    cmd_pub.publish(msg)


if __name__ == "__main__":
    t = 0.0
    while True:
        set_command(0.4, 0.5 * math.sin(0.4 * t))
        t += 0.02
        time.sleep(0.02)
