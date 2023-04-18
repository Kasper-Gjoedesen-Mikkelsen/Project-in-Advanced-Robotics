from rtde_control import RTDEControlInterface as RTDEControl
from rtde_receive import RTDEReceiveInterface as RTDEReceive
from rtde_io import RTDEIOInterface as RTDEIO
from rtde_receive import RTDEReceiveInterface as RTDEReceive

from Gripper.RobotiqGripper import RobotiqGripper
from Admittance.Admittance_Control_position import AdmittanceControl, AdmittanceControlQuaternion
from Admittance.Filter import Filter

import threading
import time
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

import threading

import atexit


ACCELERATION:float = 1.0

IP = "192.168.1.131"

THREAD:threading.Thread = None

TIME:float = 0.002

RUNNING: bool = True

force_measurement:list = []
speed_measurement:list = []


def goodbye(rtde_c:RTDEControl, rtde_r:RTDEReceive, gripper:RobotiqGripper):
    global RUNNING
    RUNNING = False

    # Robot
    try:
        # Stop the robot controller
        rtde_c.speedStop()
        rtde_c.stopScript()
        rtde_c.disconnect()
    except:
        print("Robot failed to terminate")

    try:
        # Disconnect the receiver
        rtde_r.disconnect()
    except:
        print("Robot failed to terminate")

    # Gripper
    try:
        if gripper is not None:
            position:int = 0 # 0-255 - Low value is open, high value is closed 
            speed:int = 50 # 0-255
            force:int = 10 # 0-255
            gripper.move_and_wait_for_pos(position=position, speed=speed, force=force)
            gripper.disconnect()
    except:
        print("Gripper failed to terminate")
    print("Program terminated")

def Grippper_example():
    position:int = 0 # 0-255 - Low value is open, high value is closed 
    speed:int = 50 # 0-255
    force:int = 10 # 0-255
    gripper.move_and_wait_for_pos(position=position, speed=speed, force=force)
    print(f"Pos: {str(gripper.get_current_position()): >3}  "
        f"Open: {gripper.is_open(): <2}  "
        f"Closed: {gripper.is_closed(): <2}  ")

# Define a function to run in the thread
def update_plot():
    global RUNNING

    # Function handler for button and slider
    def on_button_click(event):
        import signal
        print("Stop button clicked")
        os.kill(os.getpid(),  signal.SIGINT)
        exit()

    # Create the figure and axis
    fig = plt.figure(constrained_layout=False)

    # Scale the plot to the size of the screen
    fig.set_size_inches(plt.figaspect(1))

    # Add white space between subplots
    fig.subplots_adjust(hspace=0.75)

    # Create subplots for translation and rotation
    ax1 = fig.add_subplot(4, 1, 1)
    ax2 = fig.add_subplot(4, 1, 2)
    ax3 = fig.add_subplot(4, 1, 3)
    ax4 = fig.add_subplot(4, 1, 4)

    # Create the button and add it to the plot
    button_ax = plt.axes([0.05, 0.9, 0.03, 0.05])
    button = Button(button_ax, "Stop")
    button.on_clicked(on_button_click)

    # Initialize data arrays
    xdata_forces = np.array([0])
    xdata_velocity = np.array([0])
    ax1_data:dict = {
        "x": np.array([0]),
        "y": np.array([0]),
        "z": np.array([0])
    }
    ax2_data:dict = {
        "x": np.array([0]),
        "y": np.array([0]),
        "z": np.array([0])
    }
    ax3_data:dict = {
        "x": np.array([0]),
        "y": np.array([0]),
        "z": np.array([0])
    }
    ax4_data:dict = {
        "x": np.array([0]),
        "y": np.array([0]),
        "z": np.array([0])
    }
    keys = ["x", "y", "z"]

    # Plot the initial empty data
    for i in range(len(keys)):
        ax1.plot(xdata_forces, ax1_data[keys[i]], label=str(keys[i] + '[N]'))
        ax2.plot(xdata_forces, ax2_data[keys[i]], label=str(keys[i] + '[Nm]'))
        ax3.plot(xdata_velocity, ax3_data[keys[i]], label=str(keys[i] + '[m/s]'))
        ax4.plot(xdata_velocity, ax4_data[keys[i]], label=str(keys[i] + '[rad/s]'))

    # Set the legend and x labels
    for ax in [ax1, ax2, ax3, ax4]:
        ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
        ax.set_xlabel("Time (ms)")

    # Set the y labels
    ax1.set_ylabel("Newton (N)")
    ax2.set_ylabel("Torque (Nm)")
    ax3.set_ylabel("Velocity (m/s)")
    ax4.set_ylabel("Velocity (rad/s)")

    # Set the title
    ax1.set_title("Newton")
    ax2.set_title("Torque")
    ax3.set_title("Velocity (m/s)")
    ax4.set_title("Velocity (rad/s)")

    # Open the text file for reading
    file_force = open("forces.txt", "r")
    file_velocity = open("velocity.txt", "r")
    while RUNNING:
        # Read the lineS of data from the file
        lines = file_force.readlines()

        for line in lines:
            # Split the line into x and y values
            values = [float(val) for val in line.strip().split(',')]
            x = xdata_forces[-1] + TIME
            # Add the new data to the arrays
            xdata_forces = np.append(xdata_forces, x)
            for i in range(len(keys)):
                ax1_data[keys[i]] = np.append(ax1_data[keys[i]], values[i])
                ax2_data[keys[i]] = np.append(ax2_data[keys[i]], values[i+3])

        # Read the lineS of data from the file
        lines = file_velocity.readlines()

        for line in lines:
            # Split the line into x and y values
            values = [float(val) for val in line.strip().split(',')]
            x = xdata_velocity[-1] + TIME
            # Add the new data to the arrays
            xdata_velocity = np.append(xdata_velocity, x)
            for i in range(len(keys)):
                ax3_data[keys[i]] = np.append(ax3_data[keys[i]], values[i])
                ax4_data[keys[i]] = np.append(ax4_data[keys[i]], values[i+3])

        # Update the plot with the new data
        for i in range(len(keys)):
            ax1.lines[i].set_data(xdata_forces, ax1_data[keys[i]])
            ax2.lines[i].set_data(xdata_forces, ax2_data[keys[i]])
            ax3.lines[i].set_data(xdata_velocity, ax3_data[keys[i]])
            ax4.lines[i].set_data(xdata_velocity, ax4_data[keys[i]])
       
        for ax in (ax1, ax2, ax3, ax4):
            ax.relim()
            ax.autoscale_view()

        # Pause to allow the plot to update
        plt.pause(0.01)

    plt.savefig('Output.png')

    file_force.close()
    file_velocity.close()

def angleAxis_to_RotationMatrix(angle_axis):
    # Extract the angle and axis from the angle-axis representation
    angle = np.linalg.norm(angle_axis)
    axis = angle_axis / angle

    # Calculate the rotation matrix
    cos_theta = np.cos(angle)
    sin_theta = np.sin(angle)
    cross_matrix = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rotation_matrix = cos_theta * np.eye(3) + (1 - cos_theta) * np.outer(axis, axis) + sin_theta * cross_matrix

    return rotation_matrix

def wrench_transformation(tcp, tau, f, theta) -> tuple:
    
    R = angleAxis_to_RotationMatrix(tcp[3:6])

    P = tcp[0:3] + [0, 0, 0.057]
    S = np.array([[0, -P[2], P[1]],
                  [P[2], 0, -P[0]],
                  [-P[1], P[0], 0]])
        
    F_ext = -np.dot(R.T, np.dot(S, tau)) + np.dot(R.T, f)
    Tau_ext = np.dot(R.T, tau)
  
    return np.array(F_ext), np.array(Tau_ext)




if __name__ == "__main__":

    filename = 'forces.txt'
    if os.path.exists(filename):
        os.remove(filename)
    with open('forces.txt', 'w') as f:
        f.write(','.join(map(str, [0,0,0,0,0,0])) + '\n')  

    filename_vel = 'velocity.txt'
    if os.path.exists(filename_vel):
         os.remove(filename_vel)
    with open('velocity.txt', 'w') as f:
        f.write(','.join(map(str, [0,0,0,0,0,0])) + '\n')

    # Thread for force plot
    Force_thread = threading.Thread(target=update_plot)
    #Force_thread.start()
    
    
    # Create control and receive interface for the robot
    try:
        rtde_c = RTDEControl(IP)
        rtde_r = RTDEReceive(IP)
    except:
        time.sleep(1.0)
        rtde_c = RTDEControl(IP)
        rtde_r = RTDEReceive(IP)

    # Create a Robotiq gripper
    gripper = None
    '''
    gripper = RobotiqGripper()
    gripper.connect(IP, 63352)
    gripper.activate()

    # Close the gripper
    os.system(f"play -nq -t alsa synth {0.5} sine {220}")
    time.sleep(1.0)
    gripper.move_and_wait_for_pos(position=255, speed=5, force=25)
    time.sleep(1.0)
    '''
    
    # Add exit handler
    atexit.register(goodbye, rtde_c, rtde_r, gripper)

    # Zero Ft sensor
    rtde_c.zeroFtSensor()
    time.sleep(0.2)

    # Admittance control
    admittance_control: AdmittanceControl = AdmittanceControl(
        Kp=10, Kd=25, tr=1.0, sample_time=TIME)
    admittance_control_quarternion: AdmittanceControlQuaternion = AdmittanceControlQuaternion(
        Kp=2, Kd=9, tr=0.9, sample_time=TIME)
        #Kp=2, Kd=9, tr=0.9, sample_time=TIME)
    #Kp=5, Kd=2, tr=0.5
    
    # Kd Lower damping -> motion is more smooth
    # Kd higher damping -> motion is more stiff

    #KP Higher stiffness gain matrix will result in a more rigid end-effector that is harder to control,
    # KP Lower stiffness gain matrix will result in a more flexible end-effector that is easier to control, 
    # but may also make it more susceptible to external disturbances

    os.system(f"play -nq -t alsa synth {0.5} sine {440}")

    # Create the filters for the newton and torque measurements
    newton_filters = [Filter(iterations=1, input="NEWTON") for _ in range(3)]
    torque_filters = [Filter(iterations=1, input="TORQUE") for _ in range(3)] 

    # Main loop
    while RUNNING:
        t_start = rtde_c.initPeriod()
        
        # Get the current TCP force
        force_tcp = rtde_r.getActualTCPForce()
        newton, tau = wrench_transformation(tcp=rtde_r.getActualTCPPose(), tau=force_tcp[3:6], f=force_tcp[0:3])

        for axis in range(3):
            # Add the newton and torque measurement to the filter
            newton_filters[axis].add_data(force_tcp[axis])
            torque_filters[axis].add_data(force_tcp[axis+3])

        # Get the filtered measurement
        newton_force = np.array([newton_filters[axis].filter() for axis in range(3)])
        torque_force = np.array([torque_filters[axis].filter() for axis in range(3)]) 
        
        # Find the translational velocity with the and amittance control
        _, p, dp, ddp = admittance_control.Translation(wrench=newton_force, p_ref=[0, 0, 0])
        _, w, dw = admittance_control_quarternion.Rotation_Quaternion(wrench=torque_force, q_ref=[1, 0, 0, 0])

        # Set the translational velocity of the robot
        rtde_c.speedL([dp[0], dp[1], dp[2], w[0], w[1], w[2]], ACCELERATION, TIME)
        
        with open('forces.txt', 'a') as f:
            forces = np.append(newton_force, torque_force)
            f.write(','.join(map(str, forces)) + '\n')

        with open('velocity.txt', 'a') as f:
            f.write(','.join(map(str, [dp[0][0], dp[1][0], dp[2][0], w[0], w[1], w[2]])) + '\n')

        # Wait for next timestep
        rtde_c.waitPeriod(t_start)

