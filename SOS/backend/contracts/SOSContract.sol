// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract SOSContract {
    struct SOSMessage {
        string name;
        string location;
        string message;
        uint256 timestamp;
    }

    mapping(uint256 => SOSMessage) public sosMessages;
    uint256 public messageCount;

    event SOSSent(uint256 indexed messageId, string name, string location, string message, uint256 timestamp);

    function sendSOS(string memory name, string memory location, string memory message) public {
        messageCount++;
        sosMessages[messageCount] = SOSMessage(name, location, message, block.timestamp);
        
        emit SOSSent(messageCount, name, location, message, block.timestamp);
    }

    function getSOS(uint256 messageId) public view returns (string memory, string memory, string memory, uint256) {
        SOSMessage memory sos = sosMessages[messageId];
        return (sos.name, sos.location, sos.message, sos.timestamp);
    }
}
