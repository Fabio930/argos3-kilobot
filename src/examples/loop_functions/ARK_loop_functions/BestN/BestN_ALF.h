/**
 * @file <BestN_ALF.h>
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#ifndef BESTN_ALF_H
#define BESTN_ALF_H

#include <argos3/plugins/robots/kilobot/simulator/ALF.h>

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

    /** Used to communicate intial field data and construct the hierarchic map*/
    void SendStructInitInformation(CKilobotEntity &c_kilobot_entity);
    
    /** Used to communicate gps position and angle*/
    void SendInformationGPS(CKilobotEntity &c_kilobot_entity);

    void SendStateInformation(CKilobotEntity &c_kilobot_entity);
    
    Real abs_distance(const CVector2 a,const CVector2 b);

    // void UpdateLog(UInt16 Time);

private:

    /************************************/
    /*  Virtual Environment variables   */
    /************************************/
    /* virtual environment struct*/
    // UInt8 minimum_quorum_length;
    float                   committed_percentage;

    UInt8                   queue_lenght;
    UInt8                   rebroadcast;

    std::vector<CVector2>   m_vecKilobotPositions;
    std::vector<CDegrees>   m_vecKilobotOrientations;
    std::vector<Real>       m_vecLastTimeMessaged;
    std::vector<UInt8>      m_vecStart_experiment;
    std::vector<UInt8>      m_vecKilobotStates;
    std::vector<UInt8>      m_vecKilobotMsgType;
    Real                    m_fMinTimeBetweenTwoMsg;
    UInt8                   start_experiment = 0;

    // UInt16 log_counter = 0;

    /************************************/
    /*       Experiment variables       */
    /************************************/

    /* random number generator */
    CRandom::CRNG* c_rng;
    
    /* simulator seed */
    uint m_random_seed;

    /* output file for data acquisition */
    // std::ofstream m_cLog;
    UInt8 header = 0;
    UInt16 logging_time = 0;

    /* output file name*/
    std::string m_strLogFileName;

    /* data acquisition frequency in ticks */
    UInt16 m_unDataAcquisitionFrequency;
};

#endif
