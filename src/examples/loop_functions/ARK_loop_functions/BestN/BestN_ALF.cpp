/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#include "BestN_ALF.h"

/****************************************/
/****************************************/

CBestN_ALF::CBestN_ALF() :
    m_unDataAcquisitionFrequency(10){
        c_rng = CRandom::CreateRNG("argos");
}

/****************************************/
/****************************************/

CBestN_ALF::~CBestN_ALF(){}

/****************************************/
/****************************************/

void CBestN_ALF::Init(TConfigurationNode& t_node){
    /* Initialize ALF*/
    CALF::Init(t_node);
    /* Other initializations: Variables, Log file opening... */
    m_cLog.open(m_strLogFileName, std::ios_base::trunc | std::ios_base::out);
}

/****************************************/
/****************************************/

void CBestN_ALF::Reset(){
    /* Close data file */
    m_cLog.close();
    /* Reopen the file, erasing its contents */
    m_cLog.open(m_strLogFileName, std::ios_base::trunc | std::ios_base::out);
}

/****************************************/
/****************************************/

void CBestN_ALF::Destroy(){
    /* Close data file */
    m_cLog.close();
}

/****************************************/
/****************************************/

void CBestN_ALF::PostStep(){
    if(start_experiment == 1){
        log_counter++;
        if(log_counter == m_unDataAcquisitionFrequency){
            logging_time++;
            UpdateLog(logging_time);
            log_counter = 0;
        }
    }
    else if(header==0){
        UpdateLog(logging_time);
        header = 1;
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateLog(UInt16 Time){
    if(Time == 0) m_cLog << m_random_seed << '\t';
    m_cLog << std::endl;
    m_cLog << std::setw(5) << std::setfill('0') << std::fixed << Time << '\t'; 
    for(UInt8 i=0;i<m_vecKilobotPositions.size();i++){
        m_cLog << std::setw(7) <<std::setprecision(4) << std::setfill('0') << std::fixed << m_vecKilobotPositions[i].GetX() << '\t'
        << std::setw(7) <<std::setprecision(4) << std::setfill('0') << std::fixed << m_vecKilobotPositions[i].GetY() << '\t'
        << std::setw(2) << std::setfill('0') << std::fixed << m_vecKilobotStates[i]; 
        if(i < m_vecKilobotPositions.size()-1) m_cLog << '\t';
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotStates(){
    m_vecKilobotMsgType.resize(m_tKilobotEntities.size());
    m_vecLastTimeMessaged.resize(m_tKilobotEntities.size());
    m_vecStart_experiment.resize(m_tKilobotEntities.size());
    m_vecKilobotPositions.resize(m_tKilobotEntities.size());
    m_vecKilobotOrientations.resize(m_tKilobotEntities.size());
    m_vecKilobotStates.resize(m_tKilobotEntities.size());
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, m_tKilobotEntities.size() * m_fTimeForAMessage / 3.0);
    /* Setup the virtual states of a kilobot */
    std::vector<UInt8> assigned_kilo_states;
    assigned_kilo_states.resize(m_tKilobotEntities.size());
    UInt8 count = 0;
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
        UInt8 p = rand()%2;
        if(p == 1 && ++count <= m_tKilobotEntities.size()*committed_percentage) assigned_kilo_states[it]=1;
        else assigned_kilo_states[it]=0;
    }
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++) SetupInitialKilobotState(*m_tKilobotEntities[it],assigned_kilo_states[it]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity,UInt8 state){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotMsgType[unKilobotID] = 0;
    m_vecKilobotStates[unKilobotID] = state;
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupVirtualEnvironments(TConfigurationNode& t_tree){
    CSimulator &simulator = GetSimulator();
    m_random_seed = simulator.GetRandomSeed();
    /* Get the structure variables from the .argos file*/
    TConfigurationNode& tHierarchicalStructNode=GetNode(t_tree,"hierarchicStruct");
    /* Get dimensions and quality scaling factor*/
    GetNodeAttribute(tHierarchicalStructNode,"rebroadcast",rebroadcast);
    GetNodeAttribute(tHierarchicalStructNode,"committed_percentage",committed_percentage);
    GetNodeAttribute(tHierarchicalStructNode,"minimum_quorum_length",minimum_quorum_length);
    GetNodeAttribute(tHierarchicalStructNode,"quorum_scaling_factor",quorum_scaling_factor);
}

/****************************************/
/****************************************/

void CBestN_ALF::GetExperimentVariables(TConfigurationNode& t_tree){
    /* Get the experiment variables node from the .argos file */
    TConfigurationNode& tExperimentVariablesNode = GetNode(t_tree,"variables");
    /* Get the output datafile name and open it */
    GetNodeAttribute(tExperimentVariablesNode, "logfilename", m_strLogFileName);
    /* Get the frequency of data saving */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "dataacquisitionfrequency", m_unDataAcquisitionFrequency, m_unDataAcquisitionFrequency);
    /* Get the frequency of updating the environment plot */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "m_unEnvironmentPlotUpdateFrequency", m_unEnvironmentPlotUpdateFrequency, m_unEnvironmentPlotUpdateFrequency);
    /* Get the time for one kilobot message */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "timeforonemessage", m_fTimeForAMessage, m_fTimeForAMessage);
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateKilobotState(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateVirtualSensor(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    if (m_fTimeInSeconds - m_vecLastTimeMessaged[unKilobotID]< m_fMinTimeBetweenTwoMsg) return; // if the time is too short, the kilobot cannot receive a message
    for (UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i]=0; // clear all the variables used for messaging
    switch (start_experiment){
        case 0:
            /* Send init information for environment representation*/
            switch (m_vecStart_experiment[unKilobotID]){
                case 0:
                    m_vecStart_experiment[unKilobotID]=1;
                    SendStructInitInformation(c_kilobot_entity);
                    break;
                case 1:
                    m_vecStart_experiment[unKilobotID]=2;
                    SendInformationGPS(c_kilobot_entity,0);
                    break;
                case 2:
                    m_vecStart_experiment[unKilobotID]=3;
                    SendStateInformation(c_kilobot_entity);
                    break;
            }
            start_experiment=1;
            for(UInt8 i=0;i<m_vecStart_experiment.size();i++){
                if(m_vecStart_experiment[i]!=3){
                    start_experiment=0;
                    break;
                }
            }
            break;
        
        default:
            SendInformationGPS(c_kilobot_entity,1);
            break;
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SendStructInitInformation(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 0;
    tKilobotMessage.m_sType = rebroadcast;
    tKilobotMessage.m_sID = minimum_quorum_length;
    tKilobotMessage.m_sData = quorum_scaling_factor*100;
    // Fill the kilobot message by the ARK-type messages
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = tMessage.m_sID << 1;
        m_tMessages[unKilobotID].data[1+i*3] = tMessage.m_sData << 1;
        m_tMessages[unKilobotID].data[2+i*3] = tMessage.m_sType;
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity, const UInt8 Type){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = Type;
    tKilobotMessage.m_sType = 1;
    UInt8 angle = (UInt8)((m_vecKilobotOrientations[unKilobotID].GetValue()) * 0.0417);
    UInt8 valX = (UInt8)((m_vecKilobotPositions[unKilobotID].GetX() + this->GetSpace().GetArenaLimits().GetMax()[0]) * 100)*.5;
    UInt8 valY = (UInt8)((m_vecKilobotPositions[unKilobotID].GetY() + this->GetSpace().GetArenaLimits().GetMax()[1]) * 100)*.33;   
    tKilobotMessage.m_sType = (valY & 0b00000011) << 2 | tKilobotMessage.m_sType;
    tKilobotMessage.m_sID = unKilobotID << 3 | angle >> 1;
    tKilobotMessage.m_sData = valX << 4 | (valY >> 2) << 1 | (angle & 0b00000001);
    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = (tKilobotMessage.m_sID >> 3) << 1;
        m_tMessages[unKilobotID].data[1+i*3] = (tKilobotMessage.m_sData >> 4) <<2 | (tKilobotMessage.m_sID & 0b0000000100) >> 1 | (tKilobotMessage.m_sType & 0b0001);
        m_tMessages[unKilobotID].data[2+i*3] = (tKilobotMessage.m_sID & 0b0000000011) << 6 | (tKilobotMessage.m_sData & 0b0000000001) << 5 | (tKilobotMessage.m_sData & 0b0000001110) << 1 | ((tKilobotMessage.m_sType & 0b1100) >> 2);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendStateInformation(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 0;
    tKilobotMessage.m_sType = 2;
    tKilobotMessage.m_sID = unKilobotID;
    tKilobotMessage.m_sData = m_vecKilobotStates[unKilobotID];
    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = tKilobotMessage.m_sID << 1 | (tKilobotMessage.m_sType & 0b0011) >> 1;
        m_tMessages[unKilobotID].data[1+i*3] = tKilobotMessage.m_sType & 0b0001;
        m_tMessages[unKilobotID].data[2+i*3] = tKilobotMessage.m_sData;
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

Real CBestN_ALF::abs_distance(const CVector2 a, const CVector2 b){
    Real x = a.GetX()-b.GetX();
    x = x * x;
    Real y = a.GetY()-b.GetY();
    y = y * y;
    return sqrt(x + y);
}

/****************************************/
/****************************************/

CColor CBestN_ALF::GetFloorColor(const CVector2 &vec_position_on_plane){
    CColor color=CColor::WHITE;
    if(abs(vec_position_on_plane.GetX())>this->GetSpace().GetArenaLimits().GetMax()[0]-0.05 || abs(vec_position_on_plane.GetY())>this->GetSpace().GetArenaLimits().GetMax()[1]-0.05) color=CColor::BLACK;
    return color;
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
