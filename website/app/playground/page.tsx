"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Header } from "@/components/landing/Header";
import { Footer } from "@/components/landing/Footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface LogEntry {
  timestamp: string;
  type: "info" | "success" | "error" | "action";
  message: string;
}

interface AgentState {
  agentId: string | null;
  hasLease: boolean;
  leaseExpires: string | null;
  stateEntries: number;
  lastAction: string | null;
}

export default function PlaygroundPage() {
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      timestamp: new Date().toISOString(),
      type: "info",
      message: "Welcome to the SigAid Playground! Click buttons to simulate agent operations.",
    },
  ]);

  const [agentState, setAgentState] = useState<AgentState>({
    agentId: null,
    hasLease: false,
    leaseExpires: null,
    stateEntries: 0,
    lastAction: null,
  });

  const addLog = (type: LogEntry["type"], message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        type,
        message,
      },
    ]);
  };

  const generateAgentId = () => {
    const chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    let result = "";
    for (let i = 0; i < 32; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return `aid_${result}`;
  };

  const handleCreateAgent = () => {
    if (agentState.agentId) {
      addLog("error", "Agent already exists. Release it first to create a new one.");
      return;
    }

    const agentId = generateAgentId();
    addLog("action", "Generating Ed25519 keypair...");
    setTimeout(() => {
      addLog("success", `Agent created: ${agentId}`);
      setAgentState((prev) => ({ ...prev, agentId }));
    }, 500);
  };

  const handleAcquireLease = () => {
    if (!agentState.agentId) {
      addLog("error", "Create an agent first.");
      return;
    }
    if (agentState.hasLease) {
      addLog("error", "Agent already holds a lease.");
      return;
    }

    addLog("action", "Requesting lease from Authority...");
    setTimeout(() => {
      const expires = new Date(Date.now() + 600000).toISOString();
      addLog("success", `Lease acquired. Expires: ${expires}`);
      setAgentState((prev) => ({
        ...prev,
        hasLease: true,
        leaseExpires: expires,
      }));
    }, 800);
  };

  const handleRecordAction = () => {
    if (!agentState.hasLease) {
      addLog("error", "Must hold a lease to record actions.");
      return;
    }

    const actions = [
      "hotel_booking",
      "flight_reservation",
      "payment_processed",
      "document_signed",
      "data_fetched",
    ];
    const action = actions[Math.floor(Math.random() * actions.length)];

    addLog("action", `Recording action: ${action}`);
    setTimeout(() => {
      const hash = Math.random().toString(16).substring(2, 18);
      addLog(
        "success",
        `State entry #${agentState.stateEntries + 1} recorded. Hash: ${hash}...`
      );
      setAgentState((prev) => ({
        ...prev,
        stateEntries: prev.stateEntries + 1,
        lastAction: action,
      }));
    }, 400);
  };

  const handleCreateProof = () => {
    if (!agentState.agentId) {
      addLog("error", "Create an agent first.");
      return;
    }

    addLog("action", "Generating proof bundle...");
    setTimeout(() => {
      addLog("info", "Proof contains: agent_id, lease_token, state_head, signature");
      addLog("success", "Proof bundle created. Ready for verification.");
    }, 600);
  };

  const handleVerifyProof = () => {
    if (!agentState.agentId) {
      addLog("error", "Create an agent first.");
      return;
    }

    addLog("action", "Verifying proof with Authority...");
    setTimeout(() => {
      addLog("info", "Checking: signature, lease status, state chain integrity");
      if (agentState.hasLease) {
        addLog("success", "Verification PASSED. Agent identity confirmed.");
      } else {
        addLog("error", "Verification FAILED. No active lease.");
      }
    }, 1000);
  };

  const handleReleaseLease = () => {
    if (!agentState.hasLease) {
      addLog("error", "No lease to release.");
      return;
    }

    addLog("action", "Releasing lease...");
    setTimeout(() => {
      addLog("success", "Lease released. Another instance can now acquire it.");
      setAgentState((prev) => ({
        ...prev,
        hasLease: false,
        leaseExpires: null,
      }));
    }, 300);
  };

  const handleReset = () => {
    setAgentState({
      agentId: null,
      hasLease: false,
      leaseExpires: null,
      stateEntries: 0,
      lastAction: null,
    });
    setLogs([
      {
        timestamp: new Date().toISOString(),
        type: "info",
        message: "Playground reset. Ready to start fresh.",
      },
    ]);
  };

  return (
    <>
      <Header />
      <main className="min-h-screen pt-16 bg-gradient-to-b from-background to-card/30">
        <div className="container mx-auto px-4 py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <Badge variant="outline" className="mb-4">
              Interactive Demo
            </Badge>
            <h1 className="text-4xl font-bold mb-4">Playground</h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Explore SigAid's capabilities in this interactive simulator. No API
              key required.
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {/* Controls */}
            <div className="lg:col-span-1 space-y-6">
              {/* Agent State */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Agent State</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Agent ID</span>
                    <span className="font-mono text-xs">
                      {agentState.agentId
                        ? `${agentState.agentId.substring(0, 12)}...`
                        : "None"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Lease Status</span>
                    <Badge variant={agentState.hasLease ? "success" : "secondary"}>
                      {agentState.hasLease ? "Active" : "None"}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">State Entries</span>
                    <span>{agentState.stateEntries}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Last Action</span>
                    <span className="font-mono text-xs">
                      {agentState.lastAction || "None"}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleCreateAgent}
                    disabled={!!agentState.agentId}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                    Create Agent
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleAcquireLease}
                    disabled={!agentState.agentId || agentState.hasLease}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                      />
                    </svg>
                    Acquire Lease
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleRecordAction}
                    disabled={!agentState.hasLease}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    Record Action
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleCreateProof}
                    disabled={!agentState.agentId}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                      />
                    </svg>
                    Create Proof
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleVerifyProof}
                    disabled={!agentState.agentId}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    Verify Proof
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={handleReleaseLease}
                    disabled={!agentState.hasLease}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"
                      />
                    </svg>
                    Release Lease
                  </Button>
                  <hr className="my-2 border-border" />
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-muted-foreground"
                    onClick={handleReset}
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    Reset Playground
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Log & Code */}
            <div className="lg:col-span-2">
              <Card className="h-full">
                <Tabs defaultValue="log" className="h-full">
                  <CardHeader className="pb-0">
                    <TabsList>
                      <TabsTrigger value="log">Activity Log</TabsTrigger>
                      <TabsTrigger value="code">Python Code</TabsTrigger>
                    </TabsList>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <TabsContent value="log" className="mt-0">
                      <div className="bg-background rounded-lg border border-border p-4 h-[500px] overflow-y-auto font-mono text-sm">
                        {logs.map((log, index) => (
                          <div
                            key={index}
                            className={`mb-2 ${
                              log.type === "error"
                                ? "text-destructive"
                                : log.type === "success"
                                ? "text-accent"
                                : log.type === "action"
                                ? "text-primary"
                                : "text-muted-foreground"
                            }`}
                          >
                            <span className="text-muted-foreground/50">
                              [{new Date(log.timestamp).toLocaleTimeString()}]
                            </span>{" "}
                            {log.type === "error" && "ERROR: "}
                            {log.type === "success" && "OK: "}
                            {log.message}
                          </div>
                        ))}
                      </div>
                    </TabsContent>
                    <TabsContent value="code" className="mt-0">
                      <pre className="bg-background rounded-lg border border-border p-4 h-[500px] overflow-y-auto text-sm">
                        <code>{`from sigaid import AgentClient

# Create agent with cryptographic identity
agent = AgentClient.create()
print(f"Agent ID: {agent.agent_id}")

# Acquire exclusive lease
async with agent.lease() as lease:
    print(f"Lease acquired until {lease.expires_at}")

    # Record actions to state chain
    entry = await agent.record_action(
        action_type="transaction",
        data={
            "type": "hotel_booking",
            "hotel": "Grand Hyatt",
            "amount": 45000
        }
    )
    print(f"Recorded entry #{entry.sequence}")

    # Create proof for verification
    proof = agent.create_proof(
        challenge=service_challenge
    )

    # Service verifies the proof
    result = await service.verify(proof)
    if result.valid:
        print("Verified!")

# Lease automatically released`}</code>
                      </pre>
                    </TabsContent>
                  </CardContent>
                </Tabs>
              </Card>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
