/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#include "BestN_ALF.h"
#include <algorithm>
#include <cmath>

namespace {
UInt32 NextXorShift32(UInt32& unState) {
    unState ^= (unState << 13);
    unState ^= (unState >> 17);
    unState ^= (unState << 5);
    return unState;
}

UInt8 ControlModeFromString(const std::string& strControl) {
    if(strControl == "static") return 0;
    if(strControl == "linear") return 1;
    if(strControl == "sigmoid") return 2;
    if(strControl == "polynomial") return 3;
    return 0;
}
}

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
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotStates(){
    m_vecKilobotMsgType.resize(m_tKilobotEntities.size());
    m_vecLastTimeMessaged.resize(m_tKilobotEntities.size());
    m_vecStart_experiment.resize(m_tKilobotEntities.size());
    m_vecKilobotPositions.resize(m_tKilobotEntities.size());
    m_vecKilobotOrientations.resize(m_tKilobotEntities.size());
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, m_tKilobotEntities.size() * m_fTimeForAMessage / 3.0);
    /* Setup the virtual states of a kilobot */
    for(UInt16 it=0;it< m_tKilobotEntities.size();it++) SetupInitialKilobotState(*m_tKilobotEntities[it]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotMsgType[unKilobotID] = 0;
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
    GetNodeAttribute(tHierarchicalStructNode,"options",options);
    GetNodeAttribute(tHierarchicalStructNode,"eta",eta);
    GetNodeAttribute(tHierarchicalStructNode,"msgs_timeout",msgs_timeout);
    GetNodeAttribute(tHierarchicalStructNode,"msgs_n_hops",msgs_n_hops);
    GetNodeAttributeOrDefault(tHierarchicalStructNode,"adaptive_comm",adaptive_comm,static_cast<UInt8>(0));
    GetNodeAttribute(tHierarchicalStructNode,"control",control);
    GetNodeAttribute(tHierarchicalStructNode,"voting_msgs",voting_msgs);
    GetNodeAttribute(tHierarchicalStructNode,"control_parameter",control_parameter);
    eta = Min<Real>(1.0, Max<Real>(0.0, eta));
    options = Max<UInt8>(1, options);
    rebroadcast = Min<UInt8>(31, rebroadcast);
    msgs_n_hops = Min<UInt8>(31, msgs_n_hops);
    adaptive_comm = Min<UInt8>(1, adaptive_comm);
    voting_msgs = Min<UInt8>(127, voting_msgs);
    control_parameter = Min<Real>(1.0, Max<Real>(0.0, control_parameter));
    m_unControlMode = ControlModeFromString(control);
    m_unControlParameterQ = static_cast<UInt8>(std::round(control_parameter * 127.0));
    m_unEtaQ = static_cast<UInt8>(std::round(eta * 127.0));
    m_unFloorSeed = static_cast<UInt16>(m_random_seed & 0x0FFF);
    if(m_unFloorSeed == 0) {
        m_unFloorSeed = 1;
    }

    UInt32 unGridRows = 10;
    UInt32 unGridCols = 10;
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "grid_rows", unGridRows, unGridRows);
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "grid_cols", unGridCols, unGridCols);

    m_cGridFloor.Rows = unGridRows;
    m_cGridFloor.Cols = unGridCols;
    if(m_cGridFloor.Rows > 0 && m_cGridFloor.Cols > 0) {
        const CVector3& cArenaMin = this->GetSpace().GetArenaLimits().GetMin();
        const CVector3& cArenaMax = this->GetSpace().GetArenaLimits().GetMax();
        CVector3 cMin(cArenaMin.GetX() + 0.05, cArenaMin.GetY() + 0.05, cArenaMin.GetZ());
        CVector3 cMax(cArenaMax.GetX() - 0.05, cArenaMax.GetY() - 0.05, cArenaMax.GetZ());
        const Real fCellSizeX = (cMax.GetX() - cMin.GetX()) / m_cGridFloor.Cols;
        const Real fCellSizeY = (cMax.GetY() - cMin.GetY()) / m_cGridFloor.Rows;

        m_cGridFloor.XMin = cMin.GetX();
        m_cGridFloor.YMin = cMin.GetY();
        m_cGridFloor.InvCellSizeX = (fCellSizeX > 0 ? 1.0 / fCellSizeX : 0);
        m_cGridFloor.InvCellSizeY = (fCellSizeY > 0 ? 1.0 / fCellSizeY : 0);
        m_cGridFloor.ColorId.assign(m_cGridFloor.Rows * m_cGridFloor.Cols, 1);
        SetupFloorColorMap();

        const Real fGpsMinX = cMin.GetX() + cArenaMax.GetX();
        const Real fGpsMaxX = cMax.GetX() + cArenaMax.GetX();
        const Real fGpsMinY = cMin.GetY() + cArenaMax.GetY();
        const Real fGpsMaxY = cMax.GetY() + cArenaMax.GetY();
        const SInt32 nGpsMinXQ = static_cast<SInt32>(std::round(fGpsMinX * 100.0));
        const SInt32 nGpsMaxXQ = static_cast<SInt32>(std::round(fGpsMaxX * 100.0));
        const SInt32 nGpsMinYQ = static_cast<SInt32>(std::round(fGpsMinY * 100.0));
        const SInt32 nGpsMaxYQ = static_cast<SInt32>(std::round(fGpsMaxY * 100.0));
        m_unGpsMinXQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMinXQ)));
        m_unGpsMaxXQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMaxXQ)));
        m_unGpsMinYQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMinYQ)));
        m_unGpsMaxYQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMaxYQ)));
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupFloorColorMap() {
    const UInt32 unTotalCells = m_cGridFloor.Rows * m_cGridFloor.Cols;
    if(unTotalCells == 0) {
        return;
    }

    m_cGridFloor.ColorId.assign(unTotalCells, 1); // 1 = best option

    const UInt32 unWorseCells =
        static_cast<UInt32>((static_cast<UInt32>(m_unEtaQ) * unTotalCells + 63) / 127);
    if(unWorseCells == 0 || options == 1) {
        return;
    }

    const UInt8 unWorseOptions = options - 1;
    const UInt32 unBaseCount = unWorseCells / unWorseOptions;
    const UInt32 unRemainder = unWorseCells % unWorseOptions;

    UInt32 unCursor = 0;
    for(UInt8 unOpt = 0; unOpt < unWorseOptions; ++unOpt) {
        const UInt32 unCellsForThisOption = unBaseCount + (unOpt < unRemainder ? 1 : 0);
        const UInt8 unColorId = static_cast<UInt8>((unOpt % 254) + 2);
        for(UInt32 j = 0; j < unCellsForThisOption && unCursor < unWorseCells; ++j, ++unCursor) {
            m_cGridFloor.ColorId[unCursor] = unColorId;
        }
    }

    UInt32 unState = m_unFloorSeed;
    for(UInt32 i = unTotalCells - 1; i > 0; --i) {
        const UInt32 j = NextXorShift32(unState) % (i + 1);
        std::swap(m_cGridFloor.ColorId[i], m_cGridFloor.ColorId[j]);
    }
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
                    SendEnvironmentInitInformation(c_kilobot_entity);
                    break;
                case 2:
                    m_vecStart_experiment[unKilobotID]=3;
                    SendBoundsInitInformation(c_kilobot_entity);
                    break;
                case 3:
                    m_vecStart_experiment[unKilobotID]=4;
                    SendStateInformation(c_kilobot_entity);
                    break;
                case 4:
                    m_vecStart_experiment[unKilobotID]=5;
                    SendInformationGPS(c_kilobot_entity);
                    break;
            }
            start_experiment=1;
            for(size_t i = 0; i < m_vecStart_experiment.size(); ++i){
                if(m_vecStart_experiment[i]!=5){
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
    m_tMessages[unKilobotID].type = 0;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    const UInt16 unPayload = msgs_timeout & 0x3FFFu;
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    const UInt8 unPacketData = static_cast<UInt8>(((adaptive_comm & 0x01u) << 5) | (rebroadcast & 0x1Fu));
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>((0u << 6) | (unPacketData & 0x3Fu));
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendEnvironmentInitInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;

    m_tMessages[unKilobotID].type = 0;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    const UInt16 unPayload = static_cast<UInt16>(((m_cGridFloor.Rows & 0x7Fu) << 7) | (m_cGridFloor.Cols & 0x7Fu));
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>((1u << 6) | ((m_unFloorSeed >> 6) & 0x3Fu));
    /* Extra bytes carry map params so grid+map are sent in one init message. */
    m_tMessages[unKilobotID].data[3] = static_cast<UInt8>(m_unEtaQ & 0x7Fu);
    m_tMessages[unKilobotID].data[4] = static_cast<UInt8>(options & 0x7Fu);
    m_tMessages[unKilobotID].data[5] = static_cast<UInt8>(m_unFloorSeed & 0x3Fu);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendBoundsInitInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;

    m_tMessages[unKilobotID].type = 0;
    const UInt16 unPayload = static_cast<UInt16>(((m_unGpsMinXQ & 0x7Fu) << 7) | (m_unGpsMaxXQ & 0x7Fu));
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(3u << 6);
    m_tMessages[unKilobotID].data[3] = static_cast<UInt8>(m_unGpsMinYQ & 0x7Fu);
    m_tMessages[unKilobotID].data[4] = static_cast<UInt8>(m_unGpsMaxYQ & 0x7Fu);
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
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;

    m_tMessages[unKilobotID].type = 0;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;

    const UInt8 unKilobotId7b = static_cast<UInt8>(unKilobotID & 0x7Fu);
    const UInt16 unPayloadHops = static_cast<UInt16>(msgs_n_hops & 0x1Fu);
    const UInt16 unPayloadControl = static_cast<UInt16>(
        ((m_unControlMode & 0x03u) << 14) |
        ((voting_msgs & 0x7Fu) << 7) |
        (m_unControlParameterQ & 0x7Fu));

    /* Slot 0: MSG_B payload for msgs_n_hops (5 bits). */
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>(unPayloadHops >> 8);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(unPayloadHops & 0xFFu);

    /* Slot 1: MSG_B payload reused for extra init params */
    m_tMessages[unKilobotID].data[3] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[4] = static_cast<UInt8>(unPayloadControl >> 8);
    m_tMessages[unKilobotID].data[5] = static_cast<UInt8>(unPayloadControl & 0xFFu);

    /* Slot 2: dummy MSG_B packet for the same robot, ignored by kb_index logic */
    m_tMessages[unKilobotID].data[6] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[7] = 0;
    m_tMessages[unKilobotID].data[8] = 0;

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
    if(abs(vec_position_on_plane.GetX()) > this->GetSpace().GetArenaLimits().GetMax()[0] - 0.05 ||
       abs(vec_position_on_plane.GetY()) > this->GetSpace().GetArenaLimits().GetMax()[1] - 0.05) {
        return CColor::BLACK;
    }
    return m_cGridFloor.GetColorAt(vec_position_on_plane);
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
