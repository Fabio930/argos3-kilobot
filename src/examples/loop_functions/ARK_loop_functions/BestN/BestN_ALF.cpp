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
}

/****************************************/
/****************************************/

void CBestN_ALF::Reset(){
}

/****************************************/
/****************************************/

void CBestN_ALF::Destroy(){
}

/****************************************/
/****************************************/

void CBestN_ALF::PostStep(){
    if(!variation_done){
        m_fTimeInSeconds = GetSpace().GetSimulationClock()/CPhysicsEngine::GetInverseSimulationClockTick();
        if((UInt16)m_fTimeInSeconds==commitment_variation_time){
            // calculate new agents' state
            std::vector<UInt8> assigned_kilo_states;
            assigned_kilo_states.resize(m_tKilobotEntities.size());
            for(UInt16 it=0;it< m_tKilobotEntities.size();it++) assigned_kilo_states[it]=0;
            UInt8 count = 0;
            UInt8 p;
            while (true){
                for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
                    if(assigned_kilo_states[it]==0 && count<m_vecKilobotStates.size()*next_committed_percentage){
                        p = rand()%2;
                        if(p==1){
                            assigned_kilo_states[it]=1;
                            count++;
                        }
                    }
                }
                if(count>=m_vecKilobotStates.size()*next_committed_percentage) break;
            }
            for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
                m_vecKilobotStates[it] = assigned_kilo_states[it];
                SendStateInformation(*m_tKilobotEntities[it]);
            }
            for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
                m_vecKilobotStates[it] = assigned_kilo_states[it];
                SendStateInformation(*m_tKilobotEntities[it]);
            }
            variation_done = true;
        }
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
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++) assigned_kilo_states[it]=0;
    UInt8 count = 0;
    UInt8 p;
    while (true){
        for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
            if(assigned_kilo_states[it]==0 && count<m_vecKilobotStates.size()*committed_percentage){
                p = rand()%2;
                if(p==1){
                    assigned_kilo_states[it]=1;
                    count++;
                }
            }
        }
        if(count>=m_vecKilobotStates.size()*committed_percentage) break;
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
    GetNodeAttribute(tHierarchicalStructNode,"rebroadcast",rebroadcast);
    GetNodeAttribute(tHierarchicalStructNode,"committed_percentage",committed_percentage);
    GetNodeAttribute(tHierarchicalStructNode,"queue_lenght",queue_lenght);
    GetNodeAttribute(tHierarchicalStructNode,"msg_expiring_seconds",expiring_quorum_seconds);
    GetNodeAttribute(tHierarchicalStructNode,"commitment_variation_time",commitment_variation_time);
    GetNodeAttribute(tHierarchicalStructNode,"next_committed_percentage",next_committed_percentage);
    GetNodeAttribute(tHierarchicalStructNode,"quorum_threshold",quorum_threshold);
    if(commitment_variation_time==0) variation_done = true;
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
                    SendStateInformation(c_kilobot_entity);
                    break;
                case 2:
                    m_vecStart_experiment[unKilobotID]=3;
                    SendInformationGPS(c_kilobot_entity);
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
            SendInformationGPS(c_kilobot_entity);
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
    tKilobotMessage.m_sID = expiring_quorum_seconds;
    tKilobotMessage.m_sData = queue_lenght;
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
        m_tMessages[unKilobotID].data[i*3] = (UInt8)(tMessage.m_sID >> 7) << 1;
        m_tMessages[unKilobotID].data[1+i*3] = tMessage.m_sID << 1 | tMessage.m_sData >> 6;
        m_tMessages[unKilobotID].data[2+i*3] = tMessage.m_sData << 2 | tMessage.m_sType;
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 1;
    tKilobotMessage.m_sType = 0;
    UInt8 angle = (UInt8)((m_vecKilobotOrientations[unKilobotID].GetValue()) * 0.0417);
    UInt8 valX = (UInt8)((m_vecKilobotPositions[unKilobotID].GetX() + this->GetSpace().GetArenaLimits().GetMax()[0]) * 100)*.5;
    UInt8 valY = (UInt8)((m_vecKilobotPositions[unKilobotID].GetY() + this->GetSpace().GetArenaLimits().GetMax()[1]) * 100)*.5;   
    tKilobotMessage.m_sType = (valY & 0b00000111) << 1 | tKilobotMessage.m_sType;
    tKilobotMessage.m_sID = unKilobotID << 3 | angle >> 1;
    tKilobotMessage.m_sData = valX << 4 | (valY >> 3) << 1 | (angle & 0b00000001);
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
        m_tMessages[unKilobotID].data[1+i*3] = (tKilobotMessage.m_sData >> 4) <<2 | (tKilobotMessage.m_sID & 0b0000000110) >> 1;
        m_tMessages[unKilobotID].data[2+i*3] = (tKilobotMessage.m_sID & 0b0000000001) << 7 | (tKilobotMessage.m_sData & 0b0000000001) << 6 | (tKilobotMessage.m_sData & 0b0000001110) << 2 | ((tKilobotMessage.m_sType & 0b1110) >> 1);
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
    tKilobotMessage.m_sType = 1;
    tKilobotMessage.m_sID = unKilobotID;
    tKilobotMessage.m_sID           = quorum_threshold*100;
    tKilobotMessage.m_sID           = tKilobotMessage.m_sID << 7 | unKilobotID;
    tKilobotMessage.m_sData         = quorum_threshold*100;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData >> 3;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData << 5 ;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData << 1 | m_vecKilobotStates[unKilobotID];    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
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
        m_tMessages[unKilobotID].data[i*3] = tKilobotMessage.m_sID << 1 | tKilobotMessage.m_sType;
        m_tMessages[unKilobotID].data[1+i*3] = (tKilobotMessage.m_sData >> 6) << 3 | (tKilobotMessage.m_sID >> 7)  ;
        m_tMessages[unKilobotID].data[2+i*3] = tKilobotMessage.m_sData & 0b0000111111;
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
