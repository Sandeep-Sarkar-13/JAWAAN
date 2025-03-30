require("dotenv").config({ path: "../.env" });
const { ethers } = require("ethers");

const AVALANCHE_RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc";
const provider = new ethers.JsonRpcProvider(AVALANCHE_RPC_URL);

// Load private key from .env (Replace with your key)
const privateKey = process.env.AVALANCHE_PRIVATE_KEY;
if (!privateKey) {
    console.error("❌ Private key not found in .env file.");
    process.exit(1);
}
console.log("Private Key Loaded:", process.env.AVALANCHE_PRIVATE_KEY);

const wallet = new ethers.Wallet(privateKey, provider);

// Smart Contract ABI & Address
const contractABI = [
    "function sendSOS(string name, string location, string message) public",
    "event SOSSent(uint256 indexed messageId, string name, string location, string message, uint256 timestamp)"
];

const contractAddress = process.env.AVALANCHE_CONTRACT_ADDRESS; // Replace with your deployed contract address
const sosContract = new ethers.Contract(contractAddress, contractABI, wallet);

// Function to send an SOS
async function sendSOS() {
    try {
        console.log("🚀 Sending SOS transaction...");
        const tx = await sosContract.sendSOS("Test User", "12.9716,77.5946", "Emergency! Help needed.");
        console.log("🔗 Transaction Sent! Hash:", tx.hash);
        
        await tx.wait(); // Wait for confirmation
        console.log("✅ Transaction Confirmed!");
        console.log("🔍 Check on Explorer: https://testnet.snowtrace.io/tx/" + tx.hash);
    } catch (error) {
        console.error("❌ Error Sending Transaction:", error);
    }
}

sendSOS();
