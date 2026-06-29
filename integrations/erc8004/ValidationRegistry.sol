// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ValidationRegistry (Markovian Sepolia PoC build)
/// @notice Interface-faithful, non-upgradeable implementation of the ERC-8004
///         Validation Registry. Mirrors the reference ABI
///         (github.com/erc-8004/erc-8004-contracts @ master,
///          contracts/ValidationRegistryUpgradeable.sol, abis/ValidationRegistry.json)
///         signature-for-signature for validationRequest / validationResponse /
///         getValidationStatus / getAgentValidations / getValidatorRequests and the
///         two events. The reference is UUPS-upgradeable (OZ deps) and is NOT yet
///         deployed to any network (Validation section "under active update with the
///         TEE community"). This minimal build compiles with bare solc and deploys in
///         one tx so the Markovian provenance loop can be proven on Sepolia today.
///         When the canonical ValidationRegistry ships, only the address changes.
contract ValidationRegistry {
    struct Validation {
        address validatorAddress;
        uint256 agentId;
        string  requestURI;
        bytes32 requestHash;
        uint8   response;
        string  responseURI;
        bytes32 responseHash;
        string  tag;
        uint256 lastUpdate;
        bool    requested;
        bool    responded;
    }

    mapping(bytes32 => Validation) private _v;          // requestHash => Validation
    mapping(uint256 => bytes32[]) private _byAgent;     // agentId  => requestHashes
    mapping(address => bytes32[]) private _byValidator; // validator => requestHashes

    event ValidationRequest(
        address indexed validatorAddress,
        uint256 indexed agentId,
        string requestURI,
        bytes32 indexed requestHash
    );
    event ValidationResponse(
        address indexed validatorAddress,
        uint256 indexed agentId,
        bytes32 indexed requestHash,
        uint8 response,
        string responseURI,
        bytes32 responseHash,
        string tag
    );

    /// @notice An agent requests validation, naming the validator address.
    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestURI,
        bytes32 requestHash
    ) external {
        require(!_v[requestHash].requested, "request exists");
        Validation storage v = _v[requestHash];
        v.validatorAddress = validatorAddress;
        v.agentId          = agentId;
        v.requestURI       = requestURI;
        v.requestHash      = requestHash;
        v.requested        = true;
        v.lastUpdate       = block.timestamp;
        _byAgent[agentId].push(requestHash);
        _byValidator[validatorAddress].push(requestHash);
        emit ValidationRequest(validatorAddress, agentId, requestURI, requestHash);
    }

    /// @notice The named validator records its response (0..100). MUST be the
    ///         validatorAddress from the request. ERC-8004 normative rule.
    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tag
    ) external {
        Validation storage v = _v[requestHash];
        require(v.requested, "no request");
        require(msg.sender == v.validatorAddress, "only named validator");
        require(response <= 100, "response>100");
        v.response     = response;
        v.responseURI  = responseURI;
        v.responseHash = responseHash;
        v.tag          = tag;
        v.responded    = true;
        v.lastUpdate   = block.timestamp;
        emit ValidationResponse(
            v.validatorAddress, v.agentId, requestHash, response, responseURI, responseHash, tag
        );
    }

    /// @notice Returns (validatorAddress, agentId, response, responseHash, responseURI, lastUpdate).
    function getValidationStatus(bytes32 requestHash)
        external
        view
        returns (address, uint256, uint8, bytes32, string memory, uint256)
    {
        Validation storage v = _v[requestHash];
        return (v.validatorAddress, v.agentId, v.response, v.responseHash, v.responseURI, v.lastUpdate);
    }

    function getAgentValidations(uint256 agentId) external view returns (bytes32[] memory) {
        return _byAgent[agentId];
    }

    function getValidatorRequests(address validatorAddress) external view returns (bytes32[] memory) {
        return _byValidator[validatorAddress];
    }

    function getVersion() external pure returns (string memory) {
        return "markovian-poc-validation-registry/1.0";
    }
}
