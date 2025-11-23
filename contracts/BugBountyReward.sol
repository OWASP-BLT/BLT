// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/**
 * @title BugBountyReward
 * @dev Smart contract for automatic distribution of bug bounty rewards
 * @notice This contract manages reward pools and automatically distributes rewards
 * when bug submissions are approved
 */
contract BugBountyReward {
    // State variables
    address public owner;
    uint256 public totalRewardsDistributed;
    bool private locked;
    
    // Structs
    struct Hunt {
        uint256 id;
        address organization;
        uint256 rewardPool;
        bool active;
        mapping(uint256 => bool) issueRewarded;
    }
    
    struct RewardDistribution {
        uint256 huntId;
        uint256 issueId;
        address hunter;
        uint256 amount;
        uint256 timestamp;
    }
    
    // Mappings
    mapping(uint256 => Hunt) public hunts;
    mapping(address => uint256) public organizationBalance;
    mapping(uint256 => RewardDistribution[]) public huntRewards;
    
    // Events
    event HuntCreated(uint256 indexed huntId, address indexed organization, uint256 rewardPool);
    event RewardPoolFunded(uint256 indexed huntId, uint256 amount);
    event RewardDistributed(
        uint256 indexed huntId,
        uint256 indexed issueId,
        address indexed hunter,
        uint256 amount
    );
    event FundsWithdrawn(address indexed organization, uint256 amount);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier noReentrancy() {
        require(!locked, "No reentrancy");
        locked = true;
        _;
        locked = false;
    }
    
    modifier huntExists(uint256 _huntId) {
        require(hunts[_huntId].organization != address(0), "Hunt does not exist");
        _;
    }
    
    // Constructor
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @dev Create a new bug hunt with reward pool
     * @param _huntId Unique identifier for the hunt
     * @param _organization Address of the organization creating the hunt
     */
    function createHunt(uint256 _huntId, address _organization) external onlyOwner {
        require(hunts[_huntId].organization == address(0), "Hunt already exists");
        require(_organization != address(0), "Invalid organization address");
        
        Hunt storage newHunt = hunts[_huntId];
        newHunt.id = _huntId;
        newHunt.organization = _organization;
        newHunt.rewardPool = 0;
        newHunt.active = true;
        
        emit HuntCreated(_huntId, _organization, 0);
    }
    
    /**
     * @dev Fund a hunt's reward pool
     * @param _huntId ID of the hunt to fund
     */
    function fundHunt(uint256 _huntId) external payable huntExists(_huntId) {
        require(msg.value > 0, "Must send ETH to fund hunt");
        require(hunts[_huntId].active, "Hunt is not active");
        
        hunts[_huntId].rewardPool += msg.value;
        organizationBalance[hunts[_huntId].organization] += msg.value;
        
        emit RewardPoolFunded(_huntId, msg.value);
    }
    
    /**
     * @dev Distribute reward to a bug hunter upon approval
     * @param _huntId ID of the hunt
     * @param _issueId ID of the approved issue
     * @param _hunter Address of the bug hunter
     * @param _amount Amount to distribute
     */
    function distributeReward(
        uint256 _huntId,
        uint256 _issueId,
        address payable _hunter,
        uint256 _amount
    ) external onlyOwner huntExists(_huntId) noReentrancy {
        require(_hunter != address(0), "Invalid hunter address");
        require(_amount > 0, "Reward amount must be greater than 0");
        require(hunts[_huntId].active, "Hunt is not active");
        require(!hunts[_huntId].issueRewarded[_issueId], "Issue already rewarded");
        require(hunts[_huntId].rewardPool >= _amount, "Insufficient reward pool");
        
        // Mark issue as rewarded
        hunts[_huntId].issueRewarded[_issueId] = true;
        
        // Update balances
        hunts[_huntId].rewardPool -= _amount;
        organizationBalance[hunts[_huntId].organization] -= _amount;
        totalRewardsDistributed += _amount;
        
        // Record distribution
        huntRewards[_huntId].push(RewardDistribution({
            huntId: _huntId,
            issueId: _issueId,
            hunter: _hunter,
            amount: _amount,
            timestamp: block.timestamp
        }));
        
        // Transfer reward to hunter
        (bool success, ) = _hunter.call{value: _amount}("");
        require(success, "Transfer failed");
        
        emit RewardDistributed(_huntId, _issueId, _hunter, _amount);
    }
    
    /**
     * @dev Check if an issue has been rewarded
     * @param _huntId ID of the hunt
     * @param _issueId ID of the issue
     * @return bool indicating if issue was rewarded
     */
    function isIssueRewarded(uint256 _huntId, uint256 _issueId) 
        external 
        view 
        huntExists(_huntId) 
        returns (bool) 
    {
        return hunts[_huntId].issueRewarded[_issueId];
    }
    
    /**
     * @dev Get hunt reward pool balance
     * @param _huntId ID of the hunt
     * @return uint256 Current reward pool balance
     */
    function getHuntRewardPool(uint256 _huntId) 
        external 
        view 
        huntExists(_huntId) 
        returns (uint256) 
    {
        return hunts[_huntId].rewardPool;
    }
    
    /**
     * @dev Withdraw unused funds (only organization that funded)
     * @param _huntId ID of the hunt
     * @param _amount Amount to withdraw
     */
    function withdrawFunds(uint256 _huntId, uint256 _amount) 
        external 
        huntExists(_huntId)
        noReentrancy
    {
        require(msg.sender == hunts[_huntId].organization, "Only organization can withdraw");
        require(_amount > 0, "Amount must be greater than 0");
        require(hunts[_huntId].rewardPool >= _amount, "Insufficient balance");
        
        hunts[_huntId].rewardPool -= _amount;
        organizationBalance[msg.sender] -= _amount;
        
        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success, "Withdrawal failed");
        
        emit FundsWithdrawn(msg.sender, _amount);
    }
    
    /**
     * @dev Deactivate a hunt
     * @param _huntId ID of the hunt to deactivate
     */
    function deactivateHunt(uint256 _huntId) external onlyOwner huntExists(_huntId) {
        hunts[_huntId].active = false;
    }
    
    /**
     * @dev Get all rewards distributed for a hunt
     * @param _huntId ID of the hunt
     * @return Array of reward distributions
     */
    function getHuntRewards(uint256 _huntId) 
        external 
        view 
        huntExists(_huntId) 
        returns (RewardDistribution[] memory) 
    {
        return huntRewards[_huntId];
    }
    
    /**
     * @dev Emergency withdrawal function for contract owner
     */
    function emergencyWithdraw() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        
        (bool success, ) = payable(owner).call{value: balance}("");
        require(success, "Emergency withdrawal failed");
    }
    
    /**
     * @dev Transfer ownership
     * @param _newOwner Address of new owner
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        owner = _newOwner;
    }
    
    // Fallback function to receive ETH
    receive() external payable {
        emit RewardPoolFunded(0, msg.value);  // Log received ETH with huntId 0 for general funding
    }
}
