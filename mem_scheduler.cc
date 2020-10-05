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
    cpuPort(params->name + ".cpu_side", this),
    // memPort(params->name + ".mem_side", this),
    nextReqEvent([this]{ processNextReqEvent(); }, name()),
    readBufferSize(params->read_buffer_size),
    writeBufferSize(params->write_buffer_size),
    numberPorts(params->nbr_channels),
    numberQueues(params->nbr_cpus),
    blocked(false)
{

    panic_if(readBufferSize == 0, "readBufferSize should be non-zero");
    panic_if(writeBufferSize == 0, "writeBufferSize "
                                    "should be non-zero");
    readQueue = new std::vector<PacketPtr>[numberQueues];
    writeQueue = new std::vector<PacketPtr>[numberQueues];
    readBlocked = new bool[numberQueues];
    writeBlocked = new bool[numberQueues];
    for (uint32_t i = 0; i < numberPorts; ++i){
        MemSidePort *port = new MemSidePort(".mem_side" +
                                            std::to_string(i), this);
        memPorts.push_back(port);
    }
    for (uint32_t i = 0; i < numberQueues; ++i){
        readBlocked[i] = false;
        writeBlocked[i] = false;
    }
}

Port &
MemScheduler::getPort(const std::string &if_name, PortID idx)
{
    // panic_if(idx != InvalidPortID, "This object doesn't support vector ports");

    // This is the name from the Python SimObject declaration (MemScheduler.py)
    if (if_name == "mem_side" && idx < memPorts.size()) {
        return *memPorts[idx];
    } else if (if_name == "cpu_side") {
        return cpuPort;
    } else {
        // pass it along to our super class
        return SimObject::getPort(if_name, idx);
    }
}

void
MemScheduler::CPUSidePort::sendPacket(PacketPtr pkt)
{
    // Note: This flow control is very simple since the memobj is blocking.

    panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");

    // If we can't send the packet across the port, store it for later.
    if (!sendTimingResp(pkt)) {
        blockedPacket = pkt;
    }
}

AddrRangeList
MemScheduler::CPUSidePort::getAddrRanges() const
{
    return owner->getAddrRanges();
}

void
MemScheduler::CPUSidePort::trySendRetry()
{
    if (needRetry && blockedPacket == nullptr) {
        // Only send a retry if the port is now completely free
        needRetry = false;
        DPRINTF(MemScheduler, "Sending retry req for %d\n", id);
        sendRetryReq();
    }
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
    if (!owner->handleRequest(pkt)) {
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

    panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");

    // If we can't send the packet across the port, store it for later.
    if (!sendTimingReq(pkt)) {
        blockedPacket = pkt;
    }
}

bool
MemScheduler::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    // Just forward to the memobj.
    return owner->handleResponse(pkt);
}

void
MemScheduler::MemSidePort::recvReqRetry()
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
MemScheduler::MemSidePort::recvRangeChange()
{
    owner->sendRangeChange();
}

bool
MemScheduler::handleRequest(PacketPtr pkt)
{
    uint32_t requestorId = pkt->req->requestorId() - 3;

    panic_if(!(pkt->isRead() || pkt->isWrite()),
             "Should only see read and writes at memory controller\n");
    if (pkt->isRead() && readBlocked[requestorId])
        return false;

    if (pkt->isWrite() && writeBlocked[requestorId])
        return false;

    DPRINTF(MemScheduler, "Got request for addr %#x\n", pkt->getAddr());

    if (pkt->isRead()){
        readQueue[requestorId].push_back(pkt);
        if(readQueue[requestorId].size() == readBufferSize)
            readBlocked[requestorId] = true;
    }
    if (pkt->isWrite()){
        writeQueue[requestorId].push_back(pkt);
        if(writeQueue[requestorId].size() == writeBufferSize)
            writeBlocked[requestorId] = true;
    }

    // TODO: Schedule send packet, ignore the rest
    if (!nextReqEvent.scheduled()){
        schedule(nextReqEvent, curTick());
        std::cout << "***************************" << std::endl;
        // std::cout << "Entered processNextReqEvent" << std::endl;
    }
    // const Addr base_addr = pkt->getAddr();
    // for (auto memPort : memPorts)
    //     // AddrRangeList addr_range = memPort->getAddrRanges();
    //     for (auto addr_range : memPort->getAddrRanges())
    //         if (addr_range.contains(base_addr) ){
    //             memPort->sendPacket(pkt);
    //         }


    return true;
}
void
MemScheduler::processNextReqEvent(){
    // //arbiter
    // std::cout << "***************************" << std::endl;
    std::cout << "Entered processNextReqEvent" << std::endl;
    if (!readQueue[0].empty())
        std::cout << readQueue[0].back() << std::endl;
    schedule(nextReqEvent, curTick() + 1);
}
bool
MemScheduler::handleResponse(PacketPtr pkt)
{
    assert(blocked);
    DPRINTF(MemScheduler, "Got response for addr %#x\n", pkt->getAddr());

    // The packet is now done. We're about to put it in the port, no need for
    // this object to continue to stall.
    // We need to free the resource before sending the packet in case the CPU
    // tries to send another request immediately (e.g., in the same callchain).
    blocked = false;

    // Simply forward to the memory port
    cpuPort.sendPacket(pkt);

    // For each of the cpu ports, if it needs to send a retry, it should do it
    // now since this memory object may be unblocked now.
    cpuPort.trySendRetry();

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
    cpuPort.sendRangeChange();
}



MemScheduler*
MemSchedulerParams::create()
{
    return new MemScheduler(this);
}
