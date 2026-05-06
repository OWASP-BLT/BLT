// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Dumped {
    string private _data;
    address public owner;
    uint256 public dumpCount;
    mapping(uint256 => string) public dumpHistory;

    event DataDumped(address indexed dumper, string data, uint256 timestamp);
    event DataRetrieved(address indexed retriever, string data, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        dumpCount = 0;
    }

    function dump(string memory newData) public {
        _data = newData;
        dumpCount++;
        dumpHistory[dumpCount] = newData;
        emit DataDumped(msg.sender, newData, block.timestamp);
    }

    function retrieve() public view returns (string memory) {
        return _data;
    }

    function getDumpHistory(uint256 index) public view returns (string memory) {
        require(index > 0 && index <= dumpCount, "Invalid index");
        return dumpHistory[index];
    }

    function clearDump() public onlyOwner {
        delete _data;
        emit DataRetrieved(msg.sender, "", block.timestamp);
    }

    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}
