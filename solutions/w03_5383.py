// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Dumped {
    address public owner;
    mapping(address => uint256) public balances;
    mapping(address => bool) public dumped;

    event Dumped(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function dump() external payable {
        require(msg.value > 0, "Must send ETH");
        require(!dumped[msg.sender], "Already dumped");
        dumped[msg.sender] = true;
        balances[msg.sender] += msg.value;
        emit Dumped(msg.sender, msg.value);
    }

    function withdraw() external {
        require(dumped[msg.sender], "Not dumped");
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        balances[msg.sender] = 0;
        dumped[msg.sender] = false;
        payable(msg.sender).transfer(amount);
        emit Withdrawn(msg.sender, amount);
    }

    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    function emergencyWithdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
