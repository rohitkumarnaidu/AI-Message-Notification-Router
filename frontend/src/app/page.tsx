"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Bell, BellOff, MessageSquare, ShieldAlert, Image as ImageIcon, Mic } from "lucide-react";

interface Message {
  message_id: string;
  action: string;
  message_type: string;
  reason: string;
  confidence: number;
  message_text: string | null;
  media_type: string | null;
  evidence_message_ids: string;
}

export default function Dashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [selectedMsg, setSelectedMsg] = useState<Message | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/messages")
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          setMessages(data.data);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch messages", err);
        setLoading(false);
      });
  }, []);

  const filteredMessages = messages.filter((m) => filter === "all" || m.action === filter);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <header className="mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
          AI Message Router
        </h1>
        <p className="mt-2 text-gray-400">Enterprise Multimodal Notification Intelligence</p>
      </header>

      {/* Stats & Filters */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4 mb-8">
        {[
          { label: "Total Processed", value: messages.length, filterVal: "all", icon: Activity, color: "text-blue-400" },
          { label: "Notified", value: messages.filter(m => m.action === 'notify').length, filterVal: "notify", icon: Bell, color: "text-green-400" },
          { label: "Digested", value: messages.filter(m => m.action === 'digest').length, filterVal: "digest", icon: MessageSquare, color: "text-yellow-400" },
          { label: "Muted", value: messages.filter(m => m.action === 'mute').length, filterVal: "mute", icon: BellOff, color: "text-red-400" },
        ].map((stat) => (
          <motion.div 
            key={stat.label}
            whileHover={{ scale: 1.02 }}
            onClick={() => setFilter(stat.filterVal)}
            className={`cursor-pointer overflow-hidden rounded-xl bg-gray-900/50 backdrop-blur-md border ${filter === stat.filterVal ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-gray-800'} p-5 transition-all`}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <stat.icon className={`h-6 w-6 ${stat.color}`} aria-hidden="true" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-400">{stat.label}</dt>
                  <dd className="text-2xl font-bold text-white">{stat.value}</dd>
                </dl>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Messages List */}
        <div className="lg:col-span-2 space-y-4 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
          <AnimatePresence>
            {filteredMessages.map((msg, idx) => (
              <motion.div
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, delay: idx < 10 ? idx * 0.05 : 0 }}
                key={msg.message_id}
                onClick={() => setSelectedMsg(msg)}
                className={`cursor-pointer rounded-xl p-5 border ${selectedMsg?.message_id === msg.message_id ? 'border-indigo-500 bg-gray-800/80' : 'border-gray-800 bg-gray-900/40 hover:bg-gray-800/60'} backdrop-blur-sm transition-colors`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-sm text-gray-500">{msg.message_id}</span>
                    {msg.action === 'notify' && <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">Notify</span>}
                    {msg.action === 'digest' && <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">Digest</span>}
                    {msg.action === 'mute' && <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">Mute</span>}
                  </div>
                  <div className="flex items-center space-x-2 text-gray-500">
                    {msg.media_type === 'image' && <ImageIcon size={16} />}
                    {msg.media_type === 'voice' && <Mic size={16} />}
                    <span className="text-xs bg-gray-800 px-2 py-1 rounded-md">{msg.message_type}</span>
                  </div>
                </div>
                <p className="text-gray-300 text-sm line-clamp-2">
                  {msg.message_text || <span className="italic text-gray-500">Multimodal content only...</span>}
                </p>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Detail Panel */}
        <div className="lg:col-span-1">
          <AnimatePresence mode="wait">
            {selectedMsg ? (
              <motion.div
                key={selectedMsg.message_id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="sticky top-10 rounded-2xl border border-gray-800 bg-gray-900/50 backdrop-blur-xl p-6 shadow-2xl"
              >
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-6">
                  <ShieldAlert className="text-indigo-400" size={20} />
                  Routing Analysis
                </h3>
                
                <div className="space-y-6">
                  <div>
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-2">Original Content</h4>
                    <div className="bg-gray-950/50 rounded-lg p-4 text-sm text-gray-300 font-mono">
                      {selectedMsg.message_text || <span className="italic text-gray-600">No text provided. Media context only.</span>}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-2">Decision Reason</h4>
                    <p className="text-sm text-gray-200 leading-relaxed bg-indigo-500/10 border border-indigo-500/20 p-4 rounded-lg">
                      {selectedMsg.reason}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-950/50 p-3 rounded-lg">
                      <h4 className="text-xs text-gray-500 mb-1">Confidence</h4>
                      <p className="text-lg font-medium text-white">{(selectedMsg.confidence * 100).toFixed(1)}%</p>
                    </div>
                    <div className="bg-gray-950/50 p-3 rounded-lg">
                      <h4 className="text-xs text-gray-500 mb-1">Evidence Depth</h4>
                      <p className="text-lg font-medium text-white">{selectedMsg.evidence_message_ids === "none" ? "0" : selectedMsg.evidence_message_ids.split(";").length} signals</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="sticky top-10 rounded-2xl border border-gray-800/50 bg-gray-900/20 border-dashed p-10 flex flex-col items-center justify-center text-center">
                <MessageSquare className="h-12 w-12 text-gray-700 mb-4" />
                <h3 className="text-lg font-medium text-gray-400">No Message Selected</h3>
                <p className="text-sm text-gray-500 mt-2">Click on any message in the timeline to view its routing analysis and safety checks.</p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}
