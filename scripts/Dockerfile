# Create a base image from ray-cpu
FROM anyscale/ray:2.24.0-py311

# Create a directory
RUN mkdir ~/app

# COPY the requirements.txt file
COPY ./requirements_inv_learning.txt /home/ray/app/requirements.txt

# Install the requirements
RUN pip install -r /home/ray/app/requirements.txt
RUN pip uninstall -y ray
RUN pip install ray[default]==2.24.0

RUN sudo apt-get update && sudo apt-get install -y \
    lsb-release curl gpg

# Install the required packages
RUN curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
RUN sudo apt-get update && sudo apt-get install -y redis-server

# Install mongodb
RUN sudo apt install -y gnupg
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
    sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
    --dearmor

RUN echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
RUN sudo apt update && sudo apt install -y mongodb-org
RUN pip install motor pymongo

EXPOSE 6379
EXPOSE 27017

# Set the working directory
WORKDIR /home/ray/app/