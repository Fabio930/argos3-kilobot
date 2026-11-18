/* Messages sent by the ALF (CBestN_ALF) to each kilobot.
 * Shared by the loop function (C++) and the kilobot behavior (C).
 *
 * Every ALF message is addressed to one robot (overhead controller) and uses
 * the 9 data bytes as:   data[0] = kilobot id, data[1] = message kind,
 * data[2..8] = payload (multi-byte values are big endian).
 *
 *  CONFIG    [2] flags  [3] rebroadcast  [4..5] msg expiring seconds
 *            [6] msgs_n_hops  [7] queue length (anonymous)  [8] k_sampling
 *  STATE     [2] initial state  [3] quorum threshold in percent
 *  ARENA     [2..3] width cm  [4..5] height cm  [6..7] confinement midline cm
 *            (x coordinate in the robot frame, ARENA_NO_MIDLINE when free)
 *  VARIATION [2..3] start s  [4..5] end s (0 = abrupt)  [6..7] seed  [8] flips
 *  GPS       [2..3] x  [4..5] y (units of GPS_UNIT_M)  [6] angle (units of GPS_ANGLE_UNIT_DEG)
 *
 * The handshake is CONFIG -> STATE -> ARENA -> [VARIATION if dynamic] -> GPS,
 * after which only GPS messages are sent. Coordinates in the robot frame go
 * from 0 to the arena width/height (arena centre = width/2, height/2).
 */
#ifndef BESTN_PROTOCOL_H
#define BESTN_PROTOCOL_H

#define ALF_MSG_CONFIG      1
#define ALF_MSG_STATE       2
#define ALF_MSG_ARENA       3
#define ALF_MSG_VARIATION   4
#define ALF_MSG_GPS         5

#define CFG_FLAG_ANONYMOUS  0x01
#define CFG_FLAG_DYNAMIC    0x02
#define CFG_FLAG_CONFINED   0x04

#define ARENA_NO_MIDLINE    0xFFFF
#define ARENA_BORDER_M      0.05

#define GPS_UNIT_M          0.02
#define GPS_ANGLE_UNIT_DEG  24

#define MAX_STATE_CHANGES   9

#endif
