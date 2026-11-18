# Compiling the code

Make sure you have ARGoS >= 3.0.0-beta52 installed!

Commands:
```shell
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ../src
make
sudo make install
```

## Lab 0
```shell
argos3 -c src/examples/experiments/kilobot_blinky.argos
```

## Lab 1.2
```shell
argos3 -c src/examples/experiments/kilobot_simple_movement.argos
```

## Lab 1.3
```shell
argos3 -c src/examples/experiments/kilobot_nonblocked_movement.argos
```

## Lab 2.1-2.2
```shell
argos3 -c src/examples/experiments/kilobot_speaker_listener.argos
```

## Lab 2.3-2.4
```shell
argos3 -c src/examples/experiments/kilobot_speaker_listener_mod.argos
```

## Lab 3
```shell
argos3 -c src/examples/experiments/kilobot_disperse.argos
```

## Lab 4
```shell
argos3 -c src/examples/experiments/kilobot_orbit.argos
```

## Lab 5
```shell
argos3 -c src/examples/experiments/kilobot_move_to_light.argos
```

## Lab 6
```shell
argos3 -c src/examples/experiments/kilobot_gradient_simple.argos
```

## Lab 7
```shell
argos3 -c src/examples/experiments/kilobot_sync.argos
```

# BestN social interaction modulation

The robot-to-robot protocol (`src/examples/behaviors/quorum_comm.*`, `quorum_structure.*`) is identical
to the one in `quorum_analysis`.

Batch (from the repository root):
```shell
./src/examples/experiments/batch/loop_runs.sh src/examples/experiments/batch kilobot_ALF_BestN.argos
```

Analysis scripts are in `analysis/`; run them from the repository root, where `proc_data/` and the result
folders are (`plot_config.json` in the working directory wins over the one in `analysis/`):
```shell
python3 analysis/dump_results.py
python3 analysis/plot_results.py
```

# Differences between Kilombo and ARGoS

## Kilombo
  * Architecture
    * Single-thread, single process wrapper around kilolib.h
      * Robots must run the same behavior
      * Global variables cannot be used to contain state
  * Models
    * Only model offered is the Kilobot
    * Motion is kinematics with simple overlap resolution
      * Robots cannot push other objects
    * Communication neglects obstructions
    * Message drop has uniform probability

## ARGoS
  * Architecture
    * Multi-thread, multi-process architecture
    * Robots can run different behaviors
    * Global variables can be used to contain state
  * Models
    * Models of Kilobot, other robots, boxes, cylinders
      * Motion is full 2D dynamics
      * Robots can push other objects
    * Communication considers obstruction
    * Message drop considers local density
