/**
 * @file <BestN_ALF.h>
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
 *
 * Loop function shared by every experiment variant. The variant is selected in
 * <hierarchicStruct> (see SetupVirtualEnvironments for the parameters):
 *   communication = "id" | "anonymous"
 *   dynamic       = "false" | "true"   (committed share changes over time)
 *   confined      = "false" | "true"   (committed left / uncommitted right of middle_x_area)
 * dynamic and confined together are rejected.
**/

#ifndef BESTN_ALF_H
#define BESTN_ALF_H

#include <argos3/plugins/robots/kilobot/simulator/ALF.h>
#include "../../../behaviors/bestN_protocol.h"

class CBestN_ALF : public CALF{

public:

    CBestN_ALF();

    virtual ~CBestN_ALF();

    virtual void Init(TConfigurationNode& t_tree);

    virtual void Reset();

    virtual void Destroy();

    virtual void PostStep();

    /** Setup the initial state of the Kilobots in the space */
    void SetupInitialKilobotStates();

    /** Setup the initial state of the kilobot pc_kilobot_entity */
    void SetupInitialKilobotState(CKilobotEntity& c_kilobot_entity, UInt8 state);

    /** Setup virtual environment */
    void SetupVirtualEnvironments(TConfigurationNode& t_tree);

    /** Get experiment variables */
    void GetExperimentVariables(TConfigurationNode& t_tree);

    /** Get the message to send to a Kilobot according to its position */
    void UpdateKilobotState(CKilobotEntity& c_kilobot_entity);

    /** Get the message to send to a Kilobot according to its position */
    void UpdateVirtualSensor(CKilobotEntity& c_kilobot_entity);

    /** Used to plot the Virtual environment on the floor */
    virtual CColor GetFloorColor(const CVector2& vec_position_on_plane);

    /** Init handshake messages (see bestN_protocol.h) */
    void SendConfigInformation(CKilobotEntity &c_kilobot_entity);

    void SendStateInformation(CKilobotEntity &c_kilobot_entity);

    void SendArenaInformation(CKilobotEntity &c_kilobot_entity);

    void SendVariationInformation(CKilobotEntity &c_kilobot_entity);

    /** Used to communicate gps position and angle*/
    void SendInformationGPS(CKilobotEntity &c_kilobot_entity);

    Real abs_distance(const CVector2 a,const CVector2 b);

private:

    /** Plan the committed-state flips of each robot (dynamic variant) */
    void SetupStateVariationPlan(const std::vector<UInt8>& vec_assigned_states);

    /** Place committed robots left and uncommitted robots right of middle_x_area (confined variant) */
    void PlaceConfinedKilobots(const std::vector<UInt8>& vec_assigned_states);

    /** Prepare an ALF message addressed to one kilobot */
    message_t& PrepareMessage(UInt16 un_kilobot_id, UInt8 un_kind, UInt8 un_type);

    void Deliver(CKilobotEntity &c_kilobot_entity, UInt16 un_kilobot_id);

    /************************************/
    /*  Virtual Environment variables   */
    /************************************/
    bool                    anonymous_comm;
    bool                    dynamic_env;
    bool                    confined_env;

    float                   committed_percentage;
    float                   quorum_threshold;
    UInt16                  expiring_quorum_sec;
    UInt8                   msgs_n_hops;
    UInt8                   rebroadcast;
    UInt8                   hop_count;
    UInt16                  queue_lenght;
    UInt8                   k_sampling;

    /* dynamic variant */
    UInt16                  start_commitment_variation_time;
    UInt16                  end_commitment_variation_time;
    float                   next_committed_percentage;
    std::vector<UInt16>     m_vecVariationSeeds;
    std::vector<UInt8>      m_vecVariationNumFlips;

    /* confined variant */
    Real                    middle_x_area;

    /* init handshake: sequence of message kinds sent before the GPS updates */
    std::vector<UInt8>      m_vecInitSequence;

    std::vector<CVector2>   m_vecKilobotPositions;
    std::vector<CDegrees>   m_vecKilobotOrientations;
    std::vector<Real>       m_vecLastTimeMessaged;
    std::vector<UInt8>      m_vecStart_experiment;
    std::vector<UInt8>      m_vecKilobotStates;
    std::vector<UInt8>      m_vecKilobotMsgType;
    Real                    m_fMinTimeBetweenTwoMsg;
    UInt8                   start_experiment = 0;

    /************************************/
    /*       Experiment variables       */
    /************************************/

    /* random number generator */
    CRandom::CRNG* c_rng;

    /* simulator seed */
    uint m_random_seed;

    /* output file name*/
    std::string m_strLogFileName;

    /* data acquisition frequency in ticks */
    UInt16 m_unDataAcquisitionFrequency;
};

#endif
