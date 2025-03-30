import { useEffect, useState } from "react";
import axios from "axios";
import { 
  FaMapMarkerAlt, 
  FaExclamationTriangle, 
  FaClock, 
  FaUser, 
  FaRegCommentDots 
} from "react-icons/fa";

const SosList = () => {
  const [sosMessages, setSosMessages] = useState([]);

  useEffect(() => {
    const fetchSosMessages = async () => {
      try {
        const response = await axios.get("https://sosavalanche.onrender.com/sos-today");
        setSosMessages(response.data);
      } catch (error) {
        console.error("Error fetching SOS messages", error);
      }
    };

    // Fetch immediately
    fetchSosMessages();

    // Poll API every 1 second
    const interval = setInterval(fetchSosMessages, 1000);

    // Cleanup function to stop interval when unmounting
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4">
      {/* Header */}
      <h2 className="text-3xl font-bold text-red-500 flex items-center gap-3">
        <FaExclamationTriangle className="animate-pulse" /> JAWAAN SOS Alerts
      </h2>

      {/* Alert Box */}
      <div className="bg-gray-800 shadow-xl p-6 rounded-lg w-full max-w-2xl mt-6 border border-gray-700">
        <h3 className="text-xl font-semibold text-gray-300 text-center mb-4 flex items-center gap-2">
          <FaClock /> Today's SOS Alerts
        </h3>

        {sosMessages.length === 0 ? (
          <p className="text-gray-400 text-center">Loading SOS for Today..........</p>
        ) : (
          <div className="space-y-6">
            {sosMessages.map((sos) => {
              const [lat, lon] = sos.location.split(",").map(coord => coord.trim());
              const mapLink = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=14`;
              return (
                <div key={sos.id} className="bg-gray-700 p-4 rounded-md shadow-sm border border-gray-600">
                  <p className="text-lg text-gray-200 font-bold flex items-center gap-2">
                    <FaUser className="text-blue-400" /> {sos.name}
                  </p>
                  <p className="text-gray-400 flex items-center gap-2 mt-2">
                    <FaRegCommentDots className="text-yellow-400" /> {sos.message}
                  </p>

                  {/* Embedded OpenStreetMap */}
                  <div className="mt-3 rounded-lg overflow-hidden border border-gray-500">
                    <iframe
                      src={`https://www.openstreetmap.org/export/embed.html?bbox=${lon},${lat},${lon},${lat}&layer=mapnik&marker=${lat},${lon}`}
                      width="100%"
                      height="250"
                      style={{ border: 0 }}
                      allowFullScreen
                      loading="lazy"
                    ></iframe>
                  </div>

                  {/* View on OpenStreetMap */}
                  <a
                    href={mapLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 text-sm flex items-center gap-2 mt-3 hover:text-blue-400"
                  >
                    <FaMapMarkerAlt /> View on Map
                  </a>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default SosList;
