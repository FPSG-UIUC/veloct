# VeloCT

Public release for VeloCT / H-Houdini. This project focuses on invariant learning for hardware verification. For a detailed overview, refer to our [ASPLOS'25 publication](https://sushant94.me/publications/25asplos-hhoudini.pdf).

## Clone the Repository

Before cloning, ensure that you have [Git LFS](https://git-lfs.github.com/) installed:

```sh
# Install Git LFS
# Ubuntu/Debian
sudo apt install git-lfs

# macOS
brew install git-lfs

git lfs install
```

Then, clone the repository:

```sh
git clone https://github.com/FPSG-UIUC/veloct.git
cd veloct
```

## Setup

### System-wide Dependencies

1. **Install and run Redis:**\
   Redis is required for distributed processing. Install and start it using:

   ```sh
   # Ubuntu/Debian
   sudo apt update && sudo apt install redis
   sudo systemctl enable redis-server --now

   # macOS
   brew install redis
   brew services start redis
   ```

2. **Install and run MongoDB (optional, required for debugging):**

   ```sh
   # Ubuntu/Debian
   sudo apt install mongodb
   sudo systemctl enable mongod --now

   # macOS
   brew tap mongodb/brew
   brew install mongodb-community@6.0
   brew services start mongodb-community@6.0
   ```

   **NOTE:** Ensure MongoDB is running without errors:

   ```sh
   sudo systemctl status mongod  # Ubuntu
   brew services list             # macOS
   ```

### Python Dependencies

This project uses [Poetry](https://python-poetry.org/) for dependency management. Ensure you have it installed:

```sh
# Ubuntu/Debian
curl -sSL https://install.python-poetry.org | python3 -

# macOS
brew install poetry
```

Then, create a new virtual environment and install dependencies:

```sh
poetry install
```

## Running the Application

### Default Run Command For Rocketchip

To start invariant learning:

```sh
python3 -m learning.learn_inv_distributed learn-invariant
```

### Running on BOOM

Current targets: `smallboom,mediumboom,largeboom,megaboom`

* First, checkout the boom branch: `git checkout boom`
* Next, prepare target: `./prepare_target.sh <target>`; The target has to be one of above target strings.
* Run the same command as as before

### Managing Logging Output

By default, logging is verbose, which may slow down invariant learning. To reduce log verbosity, set the log level to `INFO`:

```sh
LOGURU_LEVEL="INFO" python3 -m learning.learn_inv_distributed learn-invariant
```

### Retrieving Results

To print the learned invariant:

```sh
python3 -m learning.learn_inv_distributed get-invariant
```

For additional options:

```sh
python3 -m learning.learn_inv_distributed --help
```