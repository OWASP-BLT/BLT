// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DumpedToken is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens
    uint256 public constant INITIAL_SUPPLY = 500_000_000 * 10**18; // 500 million initial supply
    uint256 public constant DUMP_LIMIT = 10_000 * 10**18; // Max 10k tokens per dump
    uint256 public constant DUMP_COOLDOWN = 1 hours; // 1 hour cooldown between dumps

    mapping(address => uint256) public lastDumpTime;
    mapping(address => uint256) public totalDumped;

    event Dumped(address indexed user, uint256 amount);
    event TokensBurned(address indexed user, uint256 amount);

    constructor() ERC20("Dumped Token", "DUMPED") Ownable(msg.sender) {
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    // Mint additional tokens (only owner)
    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    // Burn tokens
    function burn(uint256 amount) external {
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        _burn(msg.sender, amount);
        emit TokensBurned(msg.sender, amount);
    }

    // Dump tokens (transfer to contract and lock)
    function dump(uint256 amount) external {
        require(amount > 0, "Amount must be > 0");
        require(amount <= DUMP_LIMIT, "Exceeds dump limit");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        require(
            block.timestamp >= lastDumpTime[msg.sender] + DUMP_COOLDOWN,
            "Cooldown active"
        );

        lastDumpTime[msg.sender] = block.timestamp;
        totalDumped[msg.sender] += amount;

        _transfer(msg.sender, address(this), amount);
        emit Dumped(msg.sender, amount);
    }

    // Withdraw dumped tokens (only owner)
    function withdrawDumped(address to, uint256 amount) external onlyOwner {
        require(amount <= balanceOf(address(this)), "Insufficient dumped balance");
        _transfer(address(this), to, amount);
    }

    // Get contract balance of dumped tokens
    function getDumpedBalance() external view returns (uint256) {
        return balanceOf(address(this));
    }

    // Get user dump info
    function getUserDumpInfo(address user) external view returns (uint256 lastDump, uint256 totalDumpedAmount) {
        return (lastDumpTime[user], totalDumped[user]);
    }
}
