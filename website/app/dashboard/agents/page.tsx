"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const agents = [
  {
    id: "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
    name: "BookingAgent",
    status: "active",
    hasLease: true,
    lastActive: "2 minutes ago",
    created: "2024-01-10",
    stateEntries: 156,
    verifications: 42,
  },
  {
    id: "aid_9Bc4RmHnK7pWqS2xF5vY8dGtM3jN1kL6",
    name: "PaymentProcessor",
    status: "idle",
    hasLease: false,
    lastActive: "3 hours ago",
    created: "2024-01-15",
    stateEntries: 191,
    verifications: 47,
  },
];

export default function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredAgents = agents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agents</h1>
          <p className="text-muted-foreground">
            Manage your cryptographic agent identities
          </p>
        </div>
        <Button variant="glow" asChild>
          <Link href="/dashboard/agents/new">
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
            New Agent
          </Link>
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          placeholder="Search agents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Usage Summary */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <div className="text-sm text-muted-foreground">Agents Used</div>
                <div className="text-2xl font-bold">
                  {agents.length}
                  <span className="text-muted-foreground text-lg font-normal">
                    {" "}
                    / 5
                  </span>
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <div className="text-sm text-muted-foreground">Active Now</div>
                <div className="text-2xl font-bold">
                  {agents.filter((a) => a.hasLease).length}
                </div>
              </div>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/docs">View Docs</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Agents List */}
      <div className="space-y-4">
        {filteredAgents.map((agent, index) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center">
                      <svg
                        className="w-6 h-6 text-primary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{agent.name}</h3>
                        <Badge
                          variant={agent.hasLease ? "success" : "secondary"}
                        >
                          {agent.hasLease ? "Lease Active" : "No Lease"}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground font-mono">
                        {agent.id}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Created {agent.created} &middot; Last active{" "}
                        {agent.lastActive}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        {agent.stateEntries}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        State entries
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        {agent.verifications}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Verifications
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                        />
                      </svg>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {filteredAgents.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium mb-1">No agents found</h3>
          <p className="text-muted-foreground mb-4">
            {searchQuery
              ? "Try a different search term"
              : "Create your first agent to get started"}
          </p>
          {!searchQuery && (
            <Button variant="glow" asChild>
              <Link href="/dashboard/agents/new">Create Agent</Link>
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
