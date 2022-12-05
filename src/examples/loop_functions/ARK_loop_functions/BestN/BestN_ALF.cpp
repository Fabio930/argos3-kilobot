/**
 * This is the source file of ALF, the ARK (Augmented Reality for Kilobots) loop function.
 *
 * Reina, A., Cope, A. J., Nikolaidis, E., Marshall, J. A. R., & Sabo, C. (2017). ARK: Augmented Reality for Kilobots.
 * IEEE Robotics and Automation Letters, 2(3), 1755–1761. https://doi.org/10.1109/LRA.2017.2700059
 *
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
 */

#include "BestN_ALF.h"

/****************************************/
/****************************************/

CBestN_ALF::CBestN_ALF() :
    m_unDataAcquisitionFrequency(10){
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
    m_cOutput.open(m_strOutputFileName, std::ios_base::trunc | std::ios_base::out);
}

/****************************************/
/****************************************/

void CBestN_ALF::Reset(){
    /* Close data file */
    m_cOutput.close();
    /* Reopen the file, erasing its contents */
    m_cOutput.open(m_strOutputFileName, std::ios_base::trunc | std::ios_base::out);
}

/****************************************/
/****************************************/

void CBestN_ALF::Destroy(){
    /* Close data file */
    m_cOutput.close();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotStates(){
    m_vecLastTimeMessaged.resize(m_tKilobotEntities.size());
    m_vecStart_experiment.resize(m_tKilobotEntities.size());
    m_vecKilobotNodes.resize(m_tKilobotEntities.size());
    m_vecKilobotPositions.resize(m_tKilobotEntities.size());
    m_vecKilobotOrientations.resize(m_tKilobotEntities.size());
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, m_tKilobotEntities.size() * m_fTimeForAMessage / 3.0);
    /* Create the virtual hierarchic environment over the arena */
    vh_floor = new ChierarchicFloor(TL,BR,m_tKilobotEntities.size(),depth,branches,10,k,1,this->GetSpace().GetArenaLimits().GetMax()[0],this->GetSpace().GetArenaLimits().GetMax()[1]);
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++){
        /* Setup the virtual states of a kilobot */
        SetupInitialKilobotState(*m_tKilobotEntities[it]);
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID=GetKilobotId(c_kilobot_entity);
    m_vecKilobotNodes[unKilobotID]={0,0,0};

}

/****************************************/
/****************************************/

void CBestN_ALF::SetupVirtualEnvironments(TConfigurationNode& t_tree){
    /* Get the structure variables from the .argos file*/
    TConfigurationNode& tHierarchicalStructNode=GetNode(t_tree,"hierarchicStruct");
    /* Get dimensions and quality scaling factor*/
    GetNodeAttribute(tHierarchicalStructNode,"depth",depth);
    GetNodeAttribute(tHierarchicalStructNode,"branches",branches);
    GetNodeAttribute(tHierarchicalStructNode,"k",k);
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
    GetNodeAttribute(tExperimentVariablesNode, "datafilename", m_strOutputFileName);
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
    UInt16 unKilobotID=GetKilobotId(c_kilobot_entity);
    if (m_fTimeInSeconds - m_vecLastTimeMessaged[unKilobotID]< m_fMinTimeBetweenTwoMsg) return; // if the time is too short, the kilobot cannot receive a message
    if(!start_experiment){
        for (int i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i]=0; // clear all the variables used for messaging
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
        for (int i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i]=0; // clear all the variables used for messaging
        SendInformationGPS(c_kilobot_entity,1);
    }
}

/****************************************/
/****************************************/
/* Send #branches, #depth, param k, ID best leaf to let agents build their maps
   and set the noisy data sampling signals    
*/
void CBestN_ALF::SendStructInitInformation(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type=0;
    
    tKilobotMessage.m_sType = 0;
    tKilobotMessage.m_sID = ((int)(k*100));
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
        m_tMessages[unKilobotID].data[i*3] = ((tKilobotMessage.m_sData >> 4) << 2) | tKilobotMessage.m_sType;
        m_tMessages[unKilobotID].data[1+i*3] = tKilobotMessage.m_sID;
        m_tMessages[unKilobotID].data[2+i*3] = ((uint8_t)tKilobotMessage.m_sData & 0b00001111);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/
/* Send GPS position and orientation */

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
        m_tMessages[unKilobotID].data[i*3] = ((tKilobotMessage.m_sID >> 4) << 2) | (tKilobotMessage.m_sType & 0b0011);
        m_tMessages[unKilobotID].data[1+i*3] = ((tKilobotMessage.m_sData >> 4) << 2) | ((tKilobotMessage.m_sID & 0b0000001111) >> 2);
        m_tMessages[unKilobotID].data[2+i*3] = ((tKilobotMessage.m_sData & 0b0000001111) << 4) | (tKilobotMessage.m_sType & 0b1100) | (tKilobotMessage.m_sID & 0b0000000011);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/
Real CBestN_ALF::abs_distance(const CVector2 a, const CVector2 b){
    Real x=a.GetX()-b.GetX();
    x = x*x;
    Real y=a.GetY()-b.GetY();
    y = y*y;
    return sqrt(x+y);
}
/****************************************/
/****************************************/

CColor CBestN_ALF::GetFloorColor(const CVector2 &vec_position_on_plane){
    CColor color=CColor::WHITE;
    return color;
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
