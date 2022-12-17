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

CBestN_ALF::~CBestN_ALF(){
}

/****************************************/
/****************************************/

void CBestN_ALF::Init(TConfigurationNode& t_node){
    /* Initialize ALF*/
    CALF::Init(t_node);
    /* Other initializations: Varibales, Log file opening... */
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

void CBestN_ALF::PostExperiment(){
    m_cLog << m_random_seed << '\t' << vh_floor->get_best_leaf()->get_id() << '\t';
    for(long unsigned int i=0;i< vh_floor->get_leafs().size();i++){
        m_cLog << vh_floor->get_leafs()[i]->get_id();
        if(i < vh_floor->get_leafs().size()-1) m_cLog << '\t';
        else m_cLog << std::endl;
    }
    for(long unsigned int i=0;i<m_vecKilobotsPositionsHistory.size();i++){
        m_cLog << m_unDataAcquisitionFrequency*i << '\t'; 
        for(long unsigned int j=0;j<m_vecKilobotsPositionsHistory[i].size();j++){
            m_cLog << m_vecKilobotsPositionsHistory[i][j] << '\t' << m_vecKilobotsNodesHistory[i][j] << '\t' << m_vecKilobotsCommitmentsHistory[i][j] << '\t' << m_vecKilobotsDistFromOptHistory[i][j]; 
            if(j < m_vecKilobotsPositionsHistory[i].size()-1) m_cLog << '\t';
        }
        if(i < m_vecKilobotsPositionsHistory.size()-1) m_cLog << std::endl;
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::PostStep(){
    if(start_experiment){
        log_counter++;
        if(log_counter == m_unDataAcquisitionFrequency){
            UpdateLog();
            log_counter = 0;
        }
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateLog(){
    m_vecKilobotsPositionsHistory.push_back(m_vecKilobotPositions);
    m_vecKilobotsNodesHistory.push_back(m_vecKilobotNodes);
    m_vecKilobotsCommitmentsHistory.push_back(m_vecKilobotCommitments);
    m_vecKilobotsDistFromOptHistory.push_back(m_vecKilobotDistFromOpt);
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotStates(){
    m_vecKilobotMsgType.resize(m_tKilobotEntities.size());
    m_vecKilobotAskLevel.resize(m_tKilobotEntities.size());
    m_vecLastTimeMessaged.resize(m_tKilobotEntities.size());
    m_vecStart_experiment.resize(m_tKilobotEntities.size());
    m_vecKilobotPositions.resize(m_tKilobotEntities.size());
    m_vecKilobotDistFromOpt.resize(m_tKilobotEntities.size());
    m_vecKilobotOrientations.resize(m_tKilobotEntities.size());
    m_vecKilobotNodes.resize(m_tKilobotEntities.size());
    m_vecKilobotCommitments.resize(m_tKilobotEntities.size());
    m_vecKilobotsPositionsHistory.reserve(m_tKilobotEntities.size());
    m_vecKilobotsDistFromOptHistory.reserve(m_tKilobotEntities.size());
    m_vecKilobotsNodesHistory.reserve(m_tKilobotEntities.size());
    m_vecKilobotsCommitmentsHistory.reserve(m_tKilobotEntities.size());
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, m_tKilobotEntities.size() * m_fTimeForAMessage / 3.0);
    /* Create the virtual hierarchic environment over the arena */
    vh_floor = new ChierarchicFloor(TL,BR,depth,branches,10,k,1,this->GetSpace().GetArenaLimits().GetMax()[0],this->GetSpace().GetArenaLimits().GetMax()[1]);
    best_leaf = c_rng->Uniform(CRange<int>(0, vh_floor->get_leafs().size()));
    vh_floor->assign_MAXutility(best_leaf);
    /* Setup the virtual states of a kilobot */
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++) SetupInitialKilobotState(*m_tKilobotEntities[it]);
    UpdateLog();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotAskLevel[unKilobotID] = -1;
    m_vecKilobotMsgType[unKilobotID] = 0;
    m_vecKilobotNodes[unKilobotID] = 0;
    m_vecKilobotCommitments[unKilobotID] = 0;
    m_vecKilobotDistFromOpt[unKilobotID] = depth;
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
    GetNodeAttribute(tHierarchicalStructNode,"depth",depth);
    GetNodeAttribute(tHierarchicalStructNode,"branches",branches);
    GetNodeAttribute(tHierarchicalStructNode,"k",k);
    GetNodeAttribute(tHierarchicalStructNode,"control_gain",control_gain);
    /* Get the coordinates for the top left and bottom right corners of the arena */
    TL = CVector2(float(this->GetSpace().GetArenaLimits().GetMin()[0]+this->GetSpace().GetArenaLimits().GetMax()[0]),float(this->GetSpace().GetArenaLimits().GetMin()[1]+this->GetSpace().GetArenaLimits().GetMax()[1]));
    BR = CVector2(float(this->GetSpace().GetArenaLimits().GetMax()[0]+this->GetSpace().GetArenaLimits().GetMax()[0]),float(this->GetSpace().GetArenaLimits().GetMax()[1]+this->GetSpace().GetArenaLimits().GetMax()[1]));
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
    CColor kilo_color = GetKilobotLedColor(c_kilobot_entity);
    if(m_vecKilobotMsgType[unKilobotID] == 0 && m_vecKilobotAskLevel[unKilobotID]>=0 && kilo_color!=CColor::BLACK){
        m_vecKilobotNodes[unKilobotID] = vh_floor->derive_node_id(m_vecKilobotAskLevel[unKilobotID],m_vecKilobotPositions[unKilobotID]);
        if (kilo_color == CColor::RED) m_vecKilobotCommitments[unKilobotID] = vh_floor->get_node(m_vecKilobotNodes[unKilobotID])->get_parent()->get_id();
        else if (kilo_color == CColor::BLUE) m_vecKilobotCommitments[unKilobotID] = m_vecKilobotNodes[unKilobotID];
        m_vecKilobotDistFromOpt[unKilobotID] = vh_floor->get_node(m_vecKilobotNodes[unKilobotID])->get_distance_from_opt();
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateVirtualSensor(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    if (m_fTimeInSeconds - m_vecLastTimeMessaged[unKilobotID]< m_fMinTimeBetweenTwoMsg) return; // if the time is too short, the kilobot cannot receive a message
    for (int i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i]=0; // clear all the variables used for messaging
    if(!start_experiment){
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
        }
        start_experiment=true;
        for(long unsigned int i=0;i<m_vecStart_experiment.size();i++){
            if(m_vecStart_experiment[i]!=2){
                start_experiment=false;
                break;
            }
        }
    }
    else{
        if(m_vecKilobotMsgType[unKilobotID] == 0){
            SendInformationGPS(c_kilobot_entity,1);
            m_vecKilobotMsgType[unKilobotID] = 1;
            if(m_vecKilobotAskLevel[unKilobotID] < depth) m_vecKilobotAskLevel[unKilobotID]++;
            else m_vecKilobotAskLevel[unKilobotID] = 0;
        }
        else{
            AskForLevel(c_kilobot_entity,m_vecKilobotAskLevel[unKilobotID]);
            m_vecKilobotMsgType[unKilobotID] = 0;
        }
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
    tKilobotMessage.m_sType = 0;
    tKilobotMessage.m_sID = control_gain << 7 | ((int)(k*100));
    tKilobotMessage.m_sData = (vh_floor->get_best_leaf()->get_id()-1) << 4;
    tKilobotMessage.m_sData = tKilobotMessage.m_sData | (depth-1) << 2 | (branches-1);
    // Fill the kilobot message by the ARK-type messages
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (int i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = ((tMessage.m_sData >> 4) << 2) | tMessage.m_sType;
        m_tMessages[unKilobotID].data[1+i*3] = tMessage.m_sID & 0b01111111;
        m_tMessages[unKilobotID].data[2+i*3] = (tMessage.m_sID >> 7 ) << 4;
        m_tMessages[unKilobotID].data[2+i*3] = m_tMessages[unKilobotID].data[2+i*3] | ((uint8_t)tMessage.m_sData & 0b00001111);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity, const int Type){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = Type;
    tKilobotMessage.m_sType = 1;
    UInt8 angle = (int)((m_vecKilobotOrientations[unKilobotID].GetValue()) * 0.0417);
    UInt8 valX = (int)(((m_vecKilobotPositions[unKilobotID].GetX() + *(vh_floor->get_offset_x())) * 100) * .5);
    UInt8 valY = (int)(((m_vecKilobotPositions[unKilobotID].GetY() + *(vh_floor->get_offset_y())) * 100) * .5);
    tKilobotMessage.m_sType = (valY & 0b00000011) << 2 | tKilobotMessage.m_sType;
    tKilobotMessage.m_sID = unKilobotID << 4 | angle;
    tKilobotMessage.m_sData = valX << 4 | valY >> 2;
    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (int i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = ((tMessage.m_sID >> 4) << 2) | (tMessage.m_sType & 0b0011);
        m_tMessages[unKilobotID].data[1+i*3] = ((tMessage.m_sData >> 4) << 2) | ((tMessage.m_sID & 0b0000001111) >> 2);
        m_tMessages[unKilobotID].data[2+i*3] = ((tMessage.m_sData & 0b0000001111) << 4) | (tMessage.m_sType & 0b1100) | (tMessage.m_sID & 0b0000000011);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::AskForLevel(CKilobotEntity &c_kilobot_entity,const int Level){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 0;
    tKilobotMessage.m_sType = 2;
    tKilobotMessage.m_sID = Level;
    tKilobotMessage.m_sData = 0;

    // Fill the kilobot message by the ARK-type messages
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (int i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = tMessage.m_sID << 2 | tMessage.m_sType;
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
    Node *leaf = vh_floor->get_best_leaf();
    if(leaf->isin(vec_position_on_plane)) color=CColor::GREEN;
    return color;
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
