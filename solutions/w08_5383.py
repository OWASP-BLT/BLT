// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DumpedSolution {
    address public owner;
    mapping(address => uint256) public balances;
    mapping(address => bool) public isRegistered;
    
    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Registered(address indexed user);
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    function register() external {
        require(!isRegistered[msg.sender], "Already registered");
        isRegistered[msg.sender] = true;
        emit Registered(msg.sender);
    }
    
    function deposit() external payable {
        require(isRegistered[msg.sender], "Not registered");
        require(msg.value > 0, "Amount must be > 0");
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }
    
    function withdraw(uint256 amount) external {
        require(isRegistered[msg.sender], "Not registered");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(amount > 0, "Amount must be > 0");
        
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdrawn(msg.sender, amount);
    }
    
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
    
    function withdrawAll() external {
        require(isRegistered[msg.sender], "Not registered");
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        
        balances[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
        emit Withdrawn(msg.sender, amount);
    }
    
    function emergencyWithdraw() external onlyOwner {
        uint256 contractBalance = address(this).balance;
        require(contractBalance > 0, "No funds");
        payable(owner).transfer(contractBalance);
    }
    
    receive() external payable {
        if (isRegistered[msg.sender]) {
            balances[msg.sender] += msg.value;
            emit Deposited(msg.sender, msg.value);
        }
    }
}
