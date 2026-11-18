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

# BestN quorum experiments

One branch (`quorum_analysis`) holds every variant of the experiment. The variant is chosen in the
`<hierarchicStruct>` node of the `.argos` file:

| variant          | `communication` | `dynamic` | `confined` | was branch                    |
|------------------|-----------------|-----------|------------|-------------------------------|
| `id_static`      | `id`            | `false`   | `false`    | `quorum_analysis`             |
| `anon_static`    | `anonymous`     | `false`   | `false`    | `Parker_replica`              |
| `id_dynamic`     | `id`            | `true`    | `false`    | `quorum_analysis_dynamic`     |
| `anon_dynamic`   | `anonymous`     | `true`    | `false`    | `Parker_replica_dynamic`      |
| `id_confined`    | `id`            | `false`   | `true`     | `quorum_analysis_segregation` |
| `anon_confined`  | `anonymous`     | `false`   | `true`     | `Parker_replica_segregation`  |

`dynamic` and `confined` cannot be used together. The robot-to-robot protocol (ID-aware / anonymous buffer,
rebroadcast policies, `hop_count`) lives in `src/examples/behaviors/quorum_comm.*` and
`quorum_structure.*`, which are identical in `QS_social_interaction_modulation`. The parameters of each variant are documented in
`src/examples/experiments/kilobot_ALF_BestN.argos`; the old branch tips are kept as `archive/<branch>` tags.

Single run with the GUI:
```shell
argos3 -c src/examples/experiments/kilobot_ALF_BestN.argos
```

Batch (from the repository root; rebuilds `build/` first, results in `results_loop_runs_<variant>/`):
```shell
./src/examples/experiments/batch/loop_runs.sh src/examples/experiments/batch kilobot_ALF_BestN.argos id_dynamic
```

Analysis: `analysis/static`, `analysis/dynamic` and `analysis/segregation` contain the scripts of the
corresponding experiments; run them from the folder that holds the result directories (renamed with the
`Oresults_` / `Presults_` / `Psresults_` prefixes they expect).

Minitests (build, buffer unit tests under AddressSanitizer, short runs of every variant):
```shell
./src/examples/experiments/minitest/run_minitests.sh
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
