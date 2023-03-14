/**
 * @file <BestN_ALF.h>
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#ifndef BESTN_ALF_H
#define BESTN_ALF_H

#include <argos3/plugins/robots/kilobot/simulator/ALF.h>
#include "hierarchicFloor.h"

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
    void SendInformationGPS(CKilobotEntity &c_kilobot_entity, const UInt8 Type);
    
    void AskForLevel(CKilobotEntity &c_kilobot_entity, const UInt8 Level);

    Real abs_distance(const CVector2 a,const CVector2 b);

    void UpdateLog(UInt16 Time);

private:

    /************************************/
    /*  Virtual Environment variables   */
    /************************************/
    /* virtual environment struct*/
    UInt8 depth,branches,control_gain;
    float k;
    CVector2 TL,BR;
    ChierarchicFloor *vh_floor;

    std::vector<CVector2> m_vecKilobotPositions;
    std::vector<CVector2> m_vecKilobotChosenPoint;
    std::vector<CDegrees> m_vecKilobotOrientations;
    std::vector<Real> m_vecLastTimeMessaged;
    std::vector<UInt8> m_vecStart_experiment;
    std::vector<UInt8> m_vecKilobotNodes;
    std::vector<UInt8> m_vecKilobotCommitments;
    std::vector<UInt8> m_vecKilobotDistFromOpt;
    std::vector<UInt8> m_vecKilobotAskLevel;
    std::vector<UInt8> m_vecKilobotMsgType;
    bool start_experiment = false;
    Real m_fMinTimeBetweenTwoMsg;

    UInt16 log_counter = 0;
    UInt8 best_leaf;

    /************************************/
    /*       Experiment variables       */
    /************************************/

    /* random number generator */
    CRandom::CRNG* c_rng;
    
    /* simulator seed */
    uint m_random_seed;

    /* output file for data acquisition */
    std::ofstream m_cLog;
    std::ofstream m_cDecPos;
    UInt8 header = 0;
    UInt16 logging_time = 0;

    /* output file name*/
    std::string m_strLogFileName;
    std::string m_strDecPosFileName;

    /* data acquisition frequency in ticks */
    UInt16 m_unDataAcquisitionFrequency;
};

#endif
