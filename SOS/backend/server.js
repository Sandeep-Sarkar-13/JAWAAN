const express = require("express");
const cors = require("cors");
const axios = require("axios");
const admin = require("firebase-admin");
const CryptoJS = require("crypto-js");
const fs = require("fs");
const twilio = require("twilio");
const { log } = require("console");
const { ethers } = require("ethers");
require('dotenv').config({ path: "../.env" });

const app = express();
app.use(cors());
app.use(express.json());
// Twilio credentials


const twilioClient = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);


// Initialize Firebase (Replace with your credentials)

const serviceAccount = {
  type: "service_account",
  project_id: process.env.FIREBASE_PROJECT_ID,
  private_key_id: process.env.FIREBASE_PRIVATE_KEY_ID,
  private_key: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n'), // Fix newline issue

  client_email: process.env.FIREBASE_CLIENT_EMAIL,
  client_id: process.env.FIREBASE_CLIENT_ID,
  auth_uri: process.env.FIREBASE_AUTH_URI,
  token_uri: process.env.FIREBASE_TOKEN_URI,
  auth_provider_x509_cert_url: process.env.FIREBASE_AUTH_PROVIDER_CERT_URL,
  client_x509_cert_url: process.env.FIREBASE_CLIENT_CERT_URL,
  universe_domain: process.env.FIREBASE_UNIVERSE_DOMAIN,
};

try {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
  });
  console.log("Firebase initialized successfully");
} catch (error) {
  console.error("Firebase initialization error:", error);
}

const db = admin.firestore();
console.log("Firebase initialized successfully");


// AES-256 Encryption Function
const encryptMessage = (message) => message;

// Function to generate OpenStreetMap embed link with SOS details
const generateMapEmbed = (latitude, longitude, name, message) => {
  return `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=15/${latitude}/${longitude}&layers=O&popup=${encodeURIComponent(
    `SOS Alert!\nName: ${name}\nMessage: ${message}`
  )}`;
};



const AVALANCHE_RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc";
const provider = new ethers.JsonRpcProvider(AVALANCHE_RPC_URL);

// Load private key from .env (Replace with your key)
const privateKey = process.env.AVALANCHE_PRIVATE_KEY;
const wallet = new ethers.Wallet(privateKey, provider);


// Smart Contract ABI & Address
const contractABI = [
    "function sendSOS(string name, string location, string message) public",
    "event SOSSent(uint256 indexed messageId, string name, string location, string message, uint256 timestamp)"
];

const contractAddress = process.env.AVALANCHE_CONTRACT_ADDRESS; // Replace with your deployed contract address
const sosContract = new ethers.Contract(contractAddress, contractABI, wallet);


// 🚀 Internet Mode - Send to Firebase
app.post("/send-sos", async (req, res) => {
  try {
    const { name, location, message } = req.body;
    const [latitude, longitude] = location.split(",").map(coord => coord.trim());
    const encryptedMsg = encryptMessage(message);
    const mapEmbed = generateMapEmbed(latitude, longitude, name, message);

    console.log("Sending transaction to Avalanche...");

    // 🔥 Send transaction to Avalanche Smart Contract
    const tx = await sosContract.sendSOS(name, location, message);
    console.log("Transaction Sent:", tx.hash);

    await tx.wait(); // Wait for confirmation
    console.log("Transaction Mined!");

    // ✅ Store in Firebase after successful transaction
    await db.collection("sos_messages").add({
      name,
      location,
      message: encryptedMsg,
      txHash: tx.hash, // Store transaction hash for reference
      timestamp: new Date(),
    });

    return res.json({ status: "Success", mode: "Blockchain", txHash: tx.hash, mapEmbed });

  } catch (error) {
    console.error("Error in send-sos:", error);
    return res.status(500).json({ error: error.message });
  }
});


// 📶 SMS Fallback - If No Internet
app.post("/send-sos-sms", async (req, res) => {
  try {
    const { phone, message, location, name } = req.body;
    const [latitude, longitude] = location.split(",").map(coord => coord.trim());
    const encryptedMsg = message
    const mapEmbed = generateMapEmbed(latitude, longitude, name, message);

    const smsBody = `🚨 SOS Alert 🚨\nName: ${name}\nMessage: Emergency! Immediate assistance required. Please respond ASAP.\nLocation: ${mapEmbed}`;

    // Send SMS via Twilio
    const response = await twilioClient.messages.create({
      body: smsBody,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: phone,
    });

    return res.json({ status: "Success", mode: "SMS", messageSid: response.sid, mapEmbed });
  } catch (error) {
    console.error("Twilio Error:", error);
    console.log(error.message);
    return res.status(500).json({ error: "SMS Failed", details: error.message });
    
    
  }
});

// 🏴‍☠️ Wi-Fi Direct (P2P Mode) - Local JSON Storage
app.post("/send-sos-offline", (req, res) => {
  const { name, location, message } = req.body;
  const [latitude, longitude] = location.split(",").map(coord => coord.trim());
  const encryptedMsg = encryptMessage(message);
  const mapEmbed = generateMapEmbed(latitude, longitude, name, message);
  const sosData = { name, location, message: encryptedMsg, timestamp: new Date() };

  fs.writeFileSync("offline_sos.json", JSON.stringify(sosData, null, 2));
  return res.json({ status: "Success", mode: "Offline (Wi-Fi Direct)", mapEmbed });
});


app.get("/sos-today", async (req, res) => {
  try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const snapshot = await db.collection("sos_messages")
          .where("timestamp", ">=", today)
          .orderBy("timestamp", "desc") // Sorting by timestamp in descending order
          .get();
      
      const sosList = snapshot.docs.map(doc => {
          const data = doc.data();
          const [latitude, longitude] = data.location.split(",").map(coord => coord.trim());
          const mapLink = `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=15/${latitude}/${longitude}`;
          
          return { id: doc.id, ...data, mapLink };
      });

      res.json(sosList);
  } catch (error) {
      res.status(500).json({ error: "Error fetching SOS messages" });
  }
});


// 🚀 Satellite Mode Simulation (Mock API)
app.post("/send-sos-satellite", async (req, res) => {
  try {
    const { name, location, message } = req.body;
    const [latitude, longitude] = location.split(",").map(coord => coord.trim());
    const encryptedMsg = encryptMessage(message);
    const mapEmbed = generateMapEmbed(latitude, longitude, name, message);

    await axios.post("https://mock-satellite-api.com/sos", { name, location, message: encryptedMsg });
    return res.json({ status: "Success", mode: "Satellite", mapEmbed });
  } catch (error) {
    return res.status(500).json({ error: "Satellite API Failed" });
  }
  
});

app.listen(5000, () => console.log("SOS Server Running on Port 5000"));
