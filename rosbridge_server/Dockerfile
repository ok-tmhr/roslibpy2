ARG ROS_DISTRO=jazzy

FROM ros:${ROS_DISTRO}-ros-core

ENV ROS_DISTRO=${ROS_DISTRO}

RUN apt-get update -qq && apt-get install -yqq --no-install-recommends \
    ros-${ROS_DISTRO}-rosbridge-suite \
    ros-${ROS_DISTRO}-examples-rclpy-minimal* \
    byobu \
    && rm -rf /var/lib/apt/list/*

SHELL ["/bin/bash", "-c"]
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

WORKDIR /app

CMD ["bash"]