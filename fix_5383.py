// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is IERC20, Ownable, ReentrancyGuard {
    string public name = "Dumped Token";
    string public symbol = "DUMP";
    uint8 public decimals = 18;
    uint256 private _totalSupply;
    
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // P2P Dump mechanism
    struct DumpOrder {
        address seller;
        uint256 amount;
        uint256 price; // in wei
        bool active;
    }
    
    DumpOrder[] public dumpOrders;
    mapping(uint256 => address) public orderOwners;
    
    event DumpCreated(uint256 indexed orderId, address indexed seller, uint256 amount, uint256 price);
    event DumpExecuted(uint256 indexed orderId, address indexed buyer, uint256 amount, uint256 totalCost);
    event DumpCancelled(uint256 indexed orderId);
    
    constructor(uint256 initialSupply) {
        _mint(msg.sender, initialSupply * 10**decimals);
    }
    
    // ERC20 implementation
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address recipient, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address sender, address recipient, uint256 amount) external override returns (bool) {
        _transfer(sender, recipient, amount);
        _approve(sender, msg.sender, _allowances[sender][msg.sender] - amount);
        return true;
    }
    
    // P2P Dump functions
    function createDumpOrder(uint256 amount, uint256 price) external {
        require(amount > 0, "Amount must be greater than 0");
        require(price > 0, "Price must be greater than 0");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        
        _transfer(msg.sender, address(this), amount);
        
        uint256 orderId = dumpOrders.length;
        dumpOrders.push(DumpOrder(msg.sender, amount, price, true));
        orderOwners[orderId] = msg.sender;
        
        emit DumpCreated(orderId, msg.sender, amount, price);
    }
    
    function executeDumpOrder(uint256 orderId) external payable nonReentrant {
        DumpOrder storage order = dumpOrders[orderId];
        require(order.active, "Order is not active");
        require(msg.value >= order.price * order.amount / 10**decimals, "Insufficient payment");
        
        uint256 totalCost = order.price * order.amount / 10**decimals;
        
        // Transfer tokens to buyer
        _transfer(address(this), msg.sender, order.amount);
        
        // Transfer payment to seller
        payable(order.seller).transfer(totalCost);
        
        // Refund excess payment
        if (msg.value > totalCost) {
            payable(msg.sender).transfer(msg.value - totalCost);
        }
        
        order.active = false;
        
        emit DumpExecuted(orderId, msg.sender, order.amount, totalCost);
    }
    
    function cancelDumpOrder(uint256 orderId) external {
        require(orderOwners[orderId] == msg.sender, "Not the order owner");
        DumpOrder storage order = dumpOrders[orderId];
        require(order.active, "Order is not active");
        
        order.active = false;
        _transfer(address(this), msg.sender, order.amount);
        
        emit DumpCancelled(orderId);
    }
    
    function getActiveOrders() external view returns (DumpOrder[] memory) {
        uint256 activeCount = 0;
        for (uint256 i = 0; i < dumpOrders.length; i++) {
            if (dumpOrders[i].active) {
                activeCount++;
            }
        }
        
        DumpOrder[] memory activeOrders = new DumpOrder[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < dumpOrders.length; i++) {
            if (dumpOrders[i].active) {
                activeOrders[index] = dumpOrders[i];
                index++;
            }
        }
        
        return activeOrders;
    }
    
    // Internal functions
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "Transfer from zero address");
        require(recipient != address(0), "Transfer to zero address");
        require(_balances[sender] >= amount, "Insufficient balance");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        
        emit Transfer(sender, recipient, amount);
    }
    
    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "Mint to zero address");
        
        _totalSupply += amount;
        _balances[account] += amount;
        
        emit Transfer(address(0), account, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "Approve from zero address");
        require(spender != address(0), "Approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    // Fallback function
    receive() external payable {}
}
