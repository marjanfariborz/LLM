/*
 * Copyright (c) 2017 Jason Lowe-Power
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#include <string>
#include "mem/mem_scheduler.hh"

#include "base/trace.hh"
#include "debug/MemScheduler.hh"

MemScheduler::MemScheduler(MemSchedulerParams *params) :
    SimObject(params),
    // cpuPort(params->name + ".cpu_side", this),
    nextReqEvent([this]{ processNextReqEvent(); }, name()),
    nextRespEvent([this]{ processNextRespEvent(); }, name()),
    readBufferSize(params->read_buffer_size),
    writeBufferSize(params->write_buffer_size),
    respBufferSize(params->resp_buffer_size),
    numberPorts(params->nbr_channels),
    numberQueues(params->nbr_cpus),
    respBlocked(false)
{

    panic_if(readBufferSize == 0, "readBufferSize should be non-zero");
    panic_if(writeBufferSize == 0, "writeBufferSize "
                                    "should be non-zero");
    for (uint32_t i = 0; i < numberQueues; ++i){
        CPUSidePort *port = new CPUSidePort(this->name() + ".cpu_side" +
                                            std::to_string(i), this);
        cpuPorts.push_back(port);
    }
    for (uint32_t i = 0; i < numberPorts; ++i){
        MemSidePort *port = new MemSidePort(this->name() + ".mem_side" +
                                            std::to_string(i), this);
        memPorts.push_back(port);
    }
    currentReadEntry = readQueues.begin();
    currentWriteEntry = writeQueues.begin();
}

Port &
MemScheduler::getPort(const std::string &if_name, PortID idx)
{

    // This is the name from the Python SimObject declaration (MemScheduler.py)
    if (if_name == "mem_side" && idx < memPorts.size()) {
        return *memPorts[idx];
    } else if (if_name == "cpu_side") {
        return *cpuPorts[idx];
    } else {
        // pass it along to our super class
        return SimObject::getPort(if_name, idx);
    }
}
// TODO: Needs to be fixed
void
MemScheduler::CPUSidePort::sendPacket(PacketPtr pkt)
{
    // Note: This flow control is very simple since the memobj is blocking.

    // panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");

    // // If we can't send the packet across the port, store it for later.
    // if (!sendTimingResp(pkt)) {
    //     blockedPacket = pkt;
    //     blocked = true;
    // }
}

AddrRangeList
MemScheduler::CPUSidePort::getAddrRanges() const
{
    return owner->getAddrRanges();
}
//sendReqretry
void
MemScheduler::CPUSidePort::trySendRetry()
{
    // if (needRetry && blockedPacket == nullptr) {
        // Only send a retry if the port is now completely free
        // needRetry = false;
        DPRINTF(MemScheduler, "Sending retry req for %d\n", id);
        sendRetryReq();
    // }
}

bool
MemScheduler::CPUSidePort::getBlocked(){
    return blocked;
}

void
MemScheduler::CPUSidePort::recvFunctional(PacketPtr pkt)
{
    // Just forward to the memobj.
    return owner->handleFunctional(pkt);
}

bool
MemScheduler::CPUSidePort::recvTimingReq(PacketPtr pkt)
{
    // Just forward to the memobj.
    if (!owner->handleRequest(this, pkt)) {
        needRetry = true;
        return false;
    } else {
        return true;
    }
}

void
MemScheduler::CPUSidePort::recvRespRetry()
{
    // We should have a blocked packet if this function is called.
    assert(blockedPacket != nullptr);

    // Grab the blocked packet.
    PacketPtr pkt = blockedPacket;
    blockedPacket = nullptr;

    // Try to resend it. It's possible that it fails again.
    sendPacket(pkt);
}

void
MemScheduler::MemSidePort::sendPacket(PacketPtr pkt)
{
    // Note: This flow control is very simple since the memobj is blocking.
    panic_if(hasBlockedEntry == true, "Should never try to send if blocked MemSide!");
    // If we can't send the packet across the port, store it for later.
    if (!sendTimingReq(pkt)) {
        blockedQueueEntry = owner->readQueues.find(pkt->req->requestorId());
        hasBlockedEntry = true;
    }
}

bool
MemScheduler::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    // Just forward to the memobj.
    return owner->handleResponse(pkt);
}

bool MemScheduler::MemSidePort::getHasBlockedEntry()
{
    return hasBlockedEntry;
}
void
MemScheduler::MemSidePort::recvReqRetry()
{
    // We should have a blocked packet if this function is called.
    assert(hasBlockedEntry == true);
    // Grab the blocked packet.
    PacketPtr pkt = blockedQueueEntry->second.front();
    blockedQueueEntry->second.pop();
    hasBlockedEntry = false;

    // Try to resend it. It's possible that it fails again.
    sendPacket(pkt);
}

void
MemScheduler::MemSidePort::recvRangeChange()
{
    owner->sendRangeChange();
}

bool
MemScheduler::handleRequest(CPUSidePort *port, PacketPtr pkt)
{
    uint32_t requestorId = pkt->req->requestorId();

    panic_if(!(pkt->isRead() || pkt->isWrite()),
             "Should only see read and writes at memory controller\n");

    std::unordered_map<RequestorID, CPUSidePort*>::const_iterator ret = retryTable.find(requestorId);
    if (ret == retryTable.end())
        retryTable[requestorId] = port;

    std::unordered_map<RequestorID, bool>::const_iterator rit = readBlocked.find(requestorId);
    if (rit == readBlocked.end())
        readBlocked[requestorId] = false;

    std::unordered_map<RequestorID, bool>::const_iterator wit = writeBlocked.find(requestorId);
    if (wit == writeBlocked.end())
        writeBlocked[requestorId] = false;

    if (pkt->isRead() && readBlocked[requestorId])
        return false;

    if (pkt->isWrite() && writeBlocked[requestorId])
        return false;

    DPRINTF(MemScheduler, "Got request for addr %#x\n", pkt->getAddr());

    if (pkt->isRead()){
        readQueues[requestorId].push(pkt);
        if(readQueues[requestorId].size() == readBufferSize)
            readBlocked[requestorId] = true;
    }
    if (pkt->isWrite()){
        writeQueues[requestorId].push(pkt);
        if(writeQueues[requestorId].size() == writeBufferSize)
            writeBlocked[requestorId] = true;
    }
    if (!nextReqEvent.scheduled()){
        if (pkt->isRead())
            currentReadEntry = readQueues.find(requestorId);
        if (pkt->isWrite())
            currentWriteEntry = writeQueues.find(requestorId);
        schedule(nextReqEvent, curTick());
    }
    return true;
}

MemScheduler::MemSidePort*
MemScheduler::findMemoryPort(PacketPtr pkt){
    const Addr base_addr = pkt->getAddr();
    for (auto memPort : memPorts)
        for (auto addr_range : memPort->getAddrRanges())
            if (addr_range.contains(base_addr)){
                return memPort;
            }
    return NULL;
}

void
MemScheduler::processNextReqEvent(){
    std::unordered_map<RequestorID, std::queue<PacketPtr> >::iterator \
                                        initialEntry = currentReadEntry;
    MemSidePort* port;
    PacketPtr pkt;

    currentReadEntry++;
    if (currentReadEntry == readQueues.end()){
            currentReadEntry = readQueues.begin();
    }
    while (true){
        if (!currentReadEntry->second.empty()){
            pkt = currentReadEntry->second.front();
            port = findMemoryPort(pkt);
            if (port->getHasBlockedEntry() == false){
                port->sendPacket(pkt);
                currentReadEntry->second.pop();
                if(currentReadEntry->second.size() == readBufferSize - 1){
                    RequestorID requestorId = currentReadEntry->first;
                    DPRINTF(MemScheduler, "Sending retry to requestorId: %d\n", requestorId);
                    CPUSidePort *cpuPort = retryTable[requestorId];
                    cpuPort->trySendRetry();
                }
                break;
            }
            else{
                if (initialEntry == currentReadEntry)
                    return;
            if (currentReadEntry != readQueues.end())
                currentReadEntry++;
            if (currentReadEntry == readQueues.end())
                currentReadEntry = readQueues.begin();
            }
        } else{
            if (initialEntry == currentReadEntry)
                return;
            if (currentReadEntry != readQueues.end())
                currentReadEntry++;
            if (currentReadEntry == readQueues.end())
                currentReadEntry = readQueues.begin();
        }
    }

    // TODO: schedule next event based on clk_freq
    schedule(nextReqEvent, curTick() + 10000);
}

void
MemScheduler::processNextRespEvent(){

    DPRINTF(MemScheduler, "Processing Response Event\n");

    PacketPtr pkt;
    pkt = respQueue.front();
    int id = pkt->req->requestorId();
    if (cpuPorts[id]->getBlocked())
        return;
    cpuPorts[id]->sendPacket(pkt);
    respQueue.pop();
    if(!respQueue.empty())
        schedule(nextRespEvent, curTick() + 100);
}

bool
MemScheduler::handleResponse(PacketPtr pkt)
{

    DPRINTF(MemScheduler, "Got response for addr %#x\n", pkt->getAddr());

//     // The packet is now done. We're about to put it in the port, no need for
//     // this object to continue to stall.
//     // We need to free the resource before sending the packet in case the CPU
//     // tries to send another request immediately (e.g., in the same callchain).
    if (respBlocked)
        return false;
    respQueue.push(pkt);
    if (respQueue.size() == respBufferSize)
        respBlocked = true;
//     // Simply forward to the memory port
//     // cpuPort.sendPacket(pkt);
    if (!nextRespEvent.scheduled())
        schedule(nextRespEvent, curTick());
//     // For each of the cpu ports, if it needs to send a retry, it should do it
//     // now since this memory object may be unblocked now.
//     // cpuPort.trySendRetry();

    return true;
}

void
MemScheduler::handleFunctional(PacketPtr pkt)
{
    // Just pass this on to the memory side to handle for now.
    const Addr base_addr = pkt->getAddr();
    // Simply forward to the memory port
    for (auto memPort : memPorts)
        // AddrRangeList addr_range = memPort->getAddrRanges();
        for (auto addr_range : memPort->getAddrRanges())
            if (addr_range.start() <= base_addr &&
                    base_addr <= addr_range.end())
                memPort->sendFunctional(pkt);
}

AddrRangeList
MemScheduler::getAddrRanges() const
{
    DPRINTF(MemScheduler, "Sending new ranges\n");
    // Just use the same ranges as whatever is on the memory side.
    AddrRangeList ret;
    // Simply forward to the memory port
    for (auto memPort : memPorts)
        // AddrRangeList addr_range = memPort->getAddrRanges();
        for (auto addr_range : memPort->getAddrRanges())
            ret.push_back(addr_range);
    return ret;
}

void
MemScheduler::sendRangeChange()
{
    for (auto cpuPort : cpuPorts)
        cpuPort->sendRangeChange();
}



MemScheduler*
MemSchedulerParams::create()
{
    return new MemScheduler(this);
}
