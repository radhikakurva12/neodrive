import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Paths to files
    test_dir = '/home/neodrive/ros2_ws/src/wheelchair_sim/test_gazebo_rviz'
    urdf_path = os.path.join(test_dir, 'test_wheelchair.urdf')
    rviz_config_path = os.path.join(test_dir, 'test_rviz.rviz')
    world_path = os.path.join(test_dir, 'test_world.sdf')

    # Read URDF content
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()

    # Environment variables for Gazebo Sim meshes and rendering
    resource_path = "/home/neodrive/ros2_ws/src:/home/neodrive/ros2_ws/install/wheelchair_sim/share:/home/neodrive/ros2_ws/install/wheel_chairr/share:/home/neodrive/ros2_ws/install"
    
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=resource_path
    )
    
    set_ign_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=resource_path
    )

    # Set rendering engine to ogre to prevent GPU out-of-memory memory crashes on low-end/Jetson devices
    set_gz_engine = SetEnvironmentVariable(
        name='GZ_RENDERING_ENGINE_TO_USE',
        value='ogre'
    )
    set_ign_engine = SetEnvironmentVariable(
        name='IGN_RENDERING_ENGINE_TO_USE',
        value='ogre'
    )

    set_software_gl = SetEnvironmentVariable(
        name='LIBGL_ALWAYS_SOFTWARE',
        value='1'
    )

    # Include Gazebo Sim launch from ros_gz_sim
    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # Node to spawn the robot model
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'wheel_chairr',
            '-topic', 'robot_description',
            '-world', 'wheelchair_rooms',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.32'
        ],
        output='screen'
    )

    # Robot State Publisher node
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True
        }]
    )

    # RViz 2 node
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        parameters=[{'use_sim_time': True}]
    )

    # parameter bridge for ROS 2 - Gazebo Sim topics
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model'
        ],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        set_gz_resource_path,
        set_ign_resource_path,
        set_gz_engine,
        set_ign_engine,
        set_software_gl,
        gazebo_sim,
        spawn_robot,
        robot_state_publisher,
        rviz2,
        bridge
    ])
