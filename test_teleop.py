#!/usr/bin/env python3

import sys
import tkinter as tk
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class TeleopGUI(Node):
    def __init__(self):
        super().__init__('teleop_gui')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.linear_speed = 0.5   # m/s
        self.angular_speed = 1.0  # rad/s
        
        self.twist = Twist()
        
        # Track pressed keys and times to filter Linux auto-repeat
        self.pressed_keys = set()
        self.last_press_time = {}
        
        # Publish timer (20Hz)
        self.timer = self.create_timer(0.05, self.timer_callback)
        self.get_logger().info("Teleop GUI initialized.")

    def timer_callback(self):
        # Determine velocities based on currently pressed keys
        linear = 0.0
        angular = 0.0
        
        if 'Up' in self.pressed_keys:
            linear -= self.linear_speed
        if 'Down' in self.pressed_keys:
            linear += self.linear_speed
        if 'Left' in self.pressed_keys:
            angular -= self.angular_speed
        if 'Right' in self.pressed_keys:
            angular += self.angular_speed
            
        self.twist.linear.x = float(linear)
        self.twist.angular.z = float(angular)
        
        # Publish the command
        self.publisher.publish(self.twist)

    def set_key_press(self, key, event_time):
        self.pressed_keys.add(key)
        self.last_press_time[key] = event_time

    def set_key_release(self, key, release_time):
        # We check after 15ms if a new Press event was received (auto-repeat).
        # In Linux, auto-repeat sends KeyRelease then KeyPress with identical/near timestamps.
        self.last_press_time.setdefault(key, 0)
        
    def confirm_release(self, key, release_time):
        # If the last press time is older or equal to release_time, it is a genuine release
        if self.last_press_time.get(key, 0) <= release_time:
            if key in self.pressed_keys:
                self.pressed_keys.remove(key)


def main():
    rclpy.init()
    node = TeleopGUI()
    
    # Initialize Tkinter GUI
    root = tk.Tk()
    root.title("Wheelchair Controller")
    root.geometry("450x320")
    root.configure(bg="#121214")
    
    # Dark UI styling elements
    header_label = tk.Label(
        root, 
        text="WHEELCHAIR CONTROL PANEL", 
        font=("Helvetica", 14, "bold"), 
        fg="#00f0ff", 
        bg="#121214"
    )
    header_label.pack(pady=15)
    
    # Grid for visual indicators
    indicator_frame = tk.Frame(root, bg="#121214")
    indicator_frame.pack(pady=10)
    
    # Create indicator widgets
    indicators = {}
    
    # Up arrow indicator
    up_lbl = tk.Label(indicator_frame, text="▲\nUP", font=("Helvetica", 10, "bold"), width=6, height=3, fg="#55555c", bg="#1e1e24", bd=2, relief="flat")
    up_lbl.grid(row=0, column=1, padx=5, pady=5)
    indicators['Up'] = up_lbl
    
    # Left arrow indicator
    left_lbl = tk.Label(indicator_frame, text="◀\nLEFT", font=("Helvetica", 10, "bold"), width=6, height=3, fg="#55555c", bg="#1e1e24", bd=2, relief="flat")
    left_lbl.grid(row=1, column=0, padx=5, pady=5)
    indicators['Left'] = left_lbl
    
    # Down arrow indicator
    down_lbl = tk.Label(indicator_frame, text="▼\nDOWN", font=("Helvetica", 10, "bold"), width=6, height=3, fg="#55555c", bg="#1e1e24", bd=2, relief="flat")
    down_lbl.grid(row=1, column=1, padx=5, pady=5)
    indicators['Down'] = down_lbl
    
    # Right arrow indicator
    right_lbl = tk.Label(indicator_frame, text="▶\nRIGHT", font=("Helvetica", 10, "bold"), width=6, height=3, fg="#55555c", bg="#1e1e24", bd=2, relief="flat")
    right_lbl.grid(row=1, column=2, padx=5, pady=5)
    indicators['Right'] = right_lbl
    
    # Status display
    status_frame = tk.Frame(root, bg="#1e1e24", bd=1, relief="solid")
    status_frame.pack(fill="x", padx=30, pady=10)
    
    val_label = tk.Label(
        status_frame, 
        text="Linear: 0.00 m/s   |   Angular: 0.00 rad/s", 
        font=("Courier", 11, "bold"), 
        fg="#39ff14", 
        bg="#1e1e24"
    )
    val_label.pack(pady=8)
    
    footer_label = tk.Label(
        root, 
        text="Keep this window focused. Press Ctrl+C in terminal or close window to exit.", 
        font=("Helvetica", 8, "italic"), 
        fg="#88888e", 
        bg="#121214"
    )
    footer_label.pack(side="bottom", pady=10)

    # Keypress & release handlers
    def on_key_press(event):
        key = event.keysym
        if key in indicators:
            node.set_key_press(key, event.time)
            indicators[key].configure(bg="#00f0ff", fg="#121214")
        elif key == 'space':
            # Stop immediately
            node.pressed_keys.clear()
            for k, lbl in indicators.items():
                lbl.configure(bg="#1e1e24", fg="#55555c")

    def on_key_release(event):
        key = event.keysym
        if key in indicators:
            node.set_key_release(key, event.time)
            # Schedule validation check to filter out repeat events
            root.after(15, lambda: perform_release(key, event.time))

    def perform_release(key, release_time):
        node.confirm_release(key, release_time)
        if key not in node.pressed_keys:
            indicators[key].configure(bg="#1e1e24", fg="#55555c")

    # Bind keys
    root.bind("<KeyPress>", on_key_press)
    root.bind("<KeyRelease>", on_key_release)

    # Main update loop to sync Tkinter and ROS 2
    def spin_step():
        try:
            if rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.0)
                # Update velocity label dynamically
                val_label.config(text=f"Linear: {node.twist.linear.x:5.2f} m/s   |   Angular: {node.twist.angular.z:5.2f} rad/s")
                root.after(10, spin_step)
        except Exception as e:
            print("Error in spin loop:", e)
            shutdown()

    def shutdown():
        node.get_logger().info("Shutting down teleop node.")
        # Publish final stop command
        stop_twist = Twist()
        node.publisher.publish(stop_twist)
        root.destroy()
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)

    # Handle window close
    root.protocol("WM_DELETE_WINDOW", shutdown)
    
    # Start periodic ROS spin callback and Tkinter main loop
    root.after(10, spin_step)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        shutdown()

if __name__ == '__main__':
    main()
