/**
 * @file <BestN_ALF.h>
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#ifndef BESTN_ALF_H
#define BESTN_ALF_H

#include <argos3/plugins/robots/kilobot/simulator/ALF.h>
#include "grid_floor.h"

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
    void SetupInitialKilobotState(CKilobotEntity& c_kilobot_entity);

    /** Setup virtual environment */
    void SetupVirtualEnvironments(TConfigurationNode& t_tree);
    void SetupFloorColorMap();
    void SendBoundsInitInformation(CKilobotEntity &c_kilobot_entity);

    /** Get experiment variables */
    void GetExperimentVariables(TConfigurationNode& t_tree);

    /** Get the message to send to a Kilobot according to its position */
    void UpdateKilobotState(CKilobotEntity& c_kilobot_entity);

    /** Get the message to send to a Kilobot according to its position */
    void UpdateVirtualSensor(CKilobotEntity& c_kilobot_entity);

    /** Used to plot the Virtual environment on the floor */
    virtual CColor GetFloorColor(const CVector2& vec_position_on_plane);

    /** Used to communicate intial field data and construct the hierarchic map*/
    void SendStructInitInformation(CKilobotEntity &c_kilobot_entity);
    
    /** Used to communicate gps position and angle*/
    void SendInformationGPS(CKilobotEntity &c_kilobot_entity);

    void SendBufferInitInformation(CKilobotEntity &c_kilobot_entity);

    void SendStateInformation(CKilobotEntity &c_kilobot_entity);

    // void UpdateLog(UInt16 Time);

private:

    /************************************/
    /*  Virtual Environment variables   */
    /************************************/
    /* virtual environment struct*/
    // UInt8 minimum_quorum_length;
    Real                    eta_init;
    Real                    eta_stop;
    UInt16                  variation_time;
    Real                    init_distr;
    Real                    control_parameter;
    UInt8                   options;
    UInt8                   voting_msgs;
    std::string             control;
    bool                    bTargetRandomWorse;
    UInt16                  msgs_timeout;
    UInt8                   msgs_n_hops;
    UInt8                   rebroadcast;
    UInt8                   adaptive_comm;
    UInt8                   m_unIdAware;
    UInt8                   m_unPrioritySamplingK;
    UInt8                   m_unControlMode;
    UInt8                   m_unControlParameterQ;
    UInt16                  m_unFloorSeed;
    UInt8                   m_unEtaQ;
    UInt8                   m_unGpsMaxXQ;
    UInt8                   m_unGpsMaxYQ;

    std::vector<CVector2>   m_vecKilobotPositions;
    std::vector<CDegrees>   m_vecKilobotOrientations;
    std::vector<Real>       m_vecLastTimeMessaged;
    std::vector<UInt8>      m_vecStart_experiment;
    std::vector<UInt8>      m_vecKilobotState;
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

    CGridFloor m_cGridFloor;
};

#endif
