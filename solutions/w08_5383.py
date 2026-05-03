// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is IERC20, Ownable, ReentrancyGuard {
    string public constant name = "Dumped Token";
    string public constant symbol = "DUMP";
    uint8 public constant decimals = 18;
    
    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // P2P Dumping mechanism
    struct DumpOrder {
        address seller;
        uint256 amount;
        uint256 price; // in wei
        bool active;
    }
    
    DumpOrder[] public dumpOrders;
    mapping(address => uint256[]) public userOrders;
    
    // Fee mechanism
    uint256 public constant FEE_PERCENT = 1; // 1% fee
    address public feeCollector;
    
    // Events
    event DumpOrderCreated(address indexed seller, uint256 orderId, uint256 amount, uint256 price);
    event DumpOrderFilled(uint256 orderId, address indexed buyer, uint256 amount, uint256 totalCost);
    event DumpOrderCancelled(uint256 orderId);
    event FeeCollected(address indexed from, uint256 amount);
    
    constructor() {
        _totalSupply = 1000000 * 10**18; // 1 million tokens
        _balances[msg.sender] = _totalSupply;
        feeCollector = msg.sender;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }
    
    // ERC20 implementation
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        require(_allowances[from][msg.sender] >= amount, "ERC20: insufficient allowance");
        _allowances[from][msg.sender] -= amount;
        _transfer(from, to, amount);
        return true;
    }
    
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "ERC20: transfer from zero address");
        require(to != address(0), "ERC20: transfer to zero address");
        require(_balances[from] >= amount, "ERC20: insufficient balance");
        
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from zero address");
        require(spender != address(0), "ERC20: approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    // P2P Dump Functions
    function createDumpOrder(uint256 amount, uint256 price) external {
        require(amount > 0, "Amount must be greater than 0");
        require(price > 0, "Price must be greater than 0");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        
        _transfer(msg.sender, address(this), amount);
        
        uint256 orderId = dumpOrders.length;
        dumpOrders.push(DumpOrder({
            seller: msg.sender,
            amount: amount,
            price: price,
            active: true
        }));
        
        userOrders[msg.sender].push(orderId);
        emit DumpOrderCreated(msg.sender, orderId, amount, price);
    }
    
    function fillDumpOrder(uint256 orderId, uint256 amount) external payable nonReentrant {
        require(orderId < dumpOrders.length, "Order does not exist");
        DumpOrder storage order = dumpOrders[orderId];
        require(order.active, "Order is not active");
        require(amount > 0 && amount <= order.amount, "Invalid amount");
        require(msg.sender != order.seller, "Cannot buy your own order");
        
        uint256 totalCost = amount * order.price;
        uint256 fee = (totalCost * FEE_PERCENT) / 100;
        uint256 sellerAmount = totalCost - fee;
        
        require(msg.value >= totalCost, "Insufficient payment");
        
        // Transfer tokens to buyer
        _transfer(address(this), msg.sender, amount);
        
        // Pay seller
        payable(order.seller).transfer(sellerAmount);
        
        // Collect fee
        payable(feeCollector).transfer(fee);
        emit FeeCollected(msg.sender, fee);
        
        // Update order
        order.amount -= amount;
        if (order.amount == 0) {
            order.active = false;
        }
        
        // Refund excess payment
        if (msg.value > totalCost) {
            payable(msg.sender).transfer(msg.value - totalCost);
        }
        
        emit DumpOrderFilled(orderId, msg.sender, amount, totalCost);
    }
    
    function cancelDumpOrder(uint256 orderId) external {
        require(orderId < dumpOrders.length, "Order does not exist");
        DumpOrder storage order = dumpOrders[orderId];
        require(order.seller == msg.sender, "Not the seller");
        require(order.active, "Order already cancelled");
        
        order.active = false;
        _transfer(address(this), msg.sender, order.amount);
        
        emit DumpOrderCancelled(orderId);
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
    
    function getUserOrders(address user) external view returns (uint256[] memory) {
        return userOrders[user];
    }
    
    // Admin functions
    function setFeeCollector(address newCollector) external onlyOwner {
        require(newCollector != address(0), "Invalid address");
        feeCollector = newCollector;
    }
    
    // Fallback function
    receive() external payable {}
}
