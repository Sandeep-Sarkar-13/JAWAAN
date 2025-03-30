import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  FaMapMarkerAlt,
  FaExclamationTriangle,
  FaUserShield,
  FaPhoneAlt,
  FaSatelliteDish,
  FaGlobe,
  FaMobileAlt,
  FaMapSigns,
  FaBell,
  FaShieldAlt,
  FaHandshake,
  FaEye,
  FaPowerOff,
} from "react-icons/fa";

const SosForm = () => {
  const [formData, setFormData] = useState({
    name: "Anonymous",
    phone: "+919831404933",
    location: "",
    message: "🚨 Emergency! Please come ASAP!",
  });

  const [isSending, setIsSending] = useState(false);
  const [sosSent, setSosSent] = useState(false);

  const navigate = useNavigate();

  // Auto-detect user's location
  useEffect(() => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setFormData((prevData) => ({
          ...prevData,
          location: `${latitude},${longitude}`,
        }));
      },
      (error) => {
        console.error("Error fetching location:", error);
      }
    );
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const sendSOS = async (mode) => {
    setIsSending(true);

    const endpoint =
      mode === "internet"
        ? "/send-sos"
        : mode === "sms"
        ? "/send-sos-sms"
        : "/send-sos-offline";

    try {
      await axios.post(`https://sosavalanche.onrender.com${endpoint}`, formData);
      setSosSent(true);
    } catch (error) {
      alert("❌ Failed to send SOS!");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white p-6">
      <div className="bg-gray-900/90 shadow-2xl p-8 rounded-2xl w-full max-w-lg border border-gray-700 backdrop-blur-lg">
        {/* Header */}
        <h2 className="text-3xl font-extrabold text-red-500 flex items-center gap-3 mb-6 animate-pulse">
          <FaExclamationTriangle className="text-yellow-400" /> SEND EMERGENCY SOS
        </h2>

        {/* Form Inputs */}
        <div className="space-y-4">
          <div className="relative">
            <FaUserShield className="absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              name="name"
              placeholder="Your Name"
              value={formData.name}
              className="w-full bg-gray-800 text-white border border-gray-600 p-3 pl-10 rounded-lg focus:ring-2 focus:ring-red-500"
              onChange={handleChange}
            />
          </div>

          <div className="relative">
            <FaPhoneAlt className="absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              name="phone"
              placeholder="Your Phone Number"
              value={formData.phone}
              className="w-full bg-gray-800 text-white border border-gray-600 p-3 pl-10 rounded-lg focus:ring-2 focus:ring-red-500"
              onChange={handleChange}
            />
          </div>

          <div className="relative">
            <FaMapMarkerAlt className="absolute left-3 top-3 text-green-400" />
            <input
              type="text"
              name="location"
              placeholder="Detecting location..."
              value={formData.location}
              className="w-full bg-gray-800 text-white border border-gray-600 p-3 pl-10 rounded-lg"
              disabled
            />
          </div>

          <div className="relative">
            <FaMapSigns className="absolute left-3 top-3 text-blue-400" />
            <textarea
              name="message"
              placeholder="Enter SOS Message"
              className="w-full bg-gray-800 text-white border border-gray-600 p-3 pl-10 rounded-lg focus:ring-2 focus:ring-red-500"
              onChange={handleChange}
            >
              {formData.message}
            </textarea>
          </div>

          {/* SOS Mode Selection Buttons */}
          <div className="grid grid-cols-3 gap-3 mt-4">
            <button
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex flex-col items-center gap-2 transition-all duration-200 active:scale-95"
              onClick={() => sendSOS("internet")}
            >
              <FaGlobe className="text-2xl" />
              <span className="text-xs">Send via Internet</span>
            </button>

            <button
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg flex flex-col items-center gap-2 transition-all duration-200 active:scale-95"
              onClick={() => sendSOS("sms")}
            >
              <FaMobileAlt className="text-2xl" />
              <span className="text-xs">Send via SMS</span>
            </button>

            <button
              className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg flex flex-col items-center gap-2 transition-all duration-200 active:scale-95"
              onClick={() => sendSOS("offline")}
            >
              <FaSatelliteDish className="text-2xl" />
              <span className="text-xs">Send via Offline Mode</span>
            </button>
          </div>

          {/* View SOS Calls Near Me Button with Radar Effect */}
          <button
            className="relative mt-6 w-full bg-red-600 hover:bg-red-700 text-white px-4 py-3 rounded-lg flex items-center justify-center gap-3 transition-all duration-200 text-lg font-bold shadow-lg active:scale-95 overflow-hidden"
            onClick={() => navigate("/sos-list")}
          >
            <FaEye className="text-2xl" />
            <span>View SOS Calls Near Me</span>
            <div className="absolute inset-0 flex justify-center items-center">
              <div className="absolute w-32 h-32 bg-red-500 opacity-10 rounded-full animate-[ping_2s_infinite]"></div>
              <div className="absolute w-20 h-20 bg-red-500 opacity-20 rounded-full animate-[ping_2s_infinite_0.5s]"></div>
              <div className="absolute w-12 h-12 bg-red-500 opacity-30 rounded-full animate-[ping_2s_infinite_1s]"></div>
            </div>
          </button>
        </div>
      </div>

      {/* SOS Sent Confirmation Modal */}
      {sosSent && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
          <div className="bg-gray-900 text-white p-6 rounded-lg shadow-lg text-center">
            <h2 className="text-xl font-bold text-green-400 mb-4">
              <FaShieldAlt className="inline-block mr-2" />
              SOS Sent Successfully!
            </h2>
            <p className="text-gray-300">
              Hold your position and stay strong. Your SOS has been received. Help is on the way!
            </p>
            <button
              className="mt-4 bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg flex items-center gap-2"
              onClick={() => setSosSent(false)}
            >
              <FaPowerOff /> Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SosForm;
