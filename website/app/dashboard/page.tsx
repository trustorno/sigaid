"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const stats = [
  {
    name: "Active Agents",
    value: "2",
    limit: "/ 5",
    change: "+1 this month",
    changeType: "positive",
  },
  {
    name: "State Entries",
    value: "347",
    limit: "/ 1,000",
    change: "35% used",
    changeType: "neutral",
  },
  {
    name: "Verifications",
    value: "89",
    limit: "/ 1,000",
    change: "9% used",
    changeType: "neutral",
  },
  {
    name: "API Calls",
    value: "1,247",
    limit: "",
    change: "Last 30 days",
    changeType: "neutral",
  },
];

const recentAgents = [
  {
    id: "aid_7Xq9YkPzN3mWvR5tH8jL2c",
    name: "BookingAgent",
    status: "active",
    lastActive: "2 minutes ago",
    entries: 156,
  },
  {
    id: "aid_9Bc4RmHnK7pWqS2xF5vY8d",
    name: "PaymentProcessor",
    status: "idle",
    lastActive: "3 hours ago",
    entries: 191,
  },
];

const recentActivity = [
  { action: "State entry recorded", agent: "BookingAgent", time: "2 min ago" },
  { action: "Lease acquired", agent: "BookingAgent", time: "5 min ago" },
  { action: "Verification request", agent: "PaymentProcessor", time: "3 hrs ago" },
  { action: "Agent created", agent: "PaymentProcessor", time: "1 day ago" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your agent infrastructure
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

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.name}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stat.value}
                  <span className="text-muted-foreground text-lg font-normal">
                    {stat.limit}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stat.change}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Agents */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Agents</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard/agents">View all</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {recentAgents.map((agent) => (
              <div
                key={agent.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <svg
                      className="w-5 h-5 text-primary"
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
                    <div className="font-medium">{agent.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">
                      {agent.id.substring(0, 16)}...
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <Badge
                    variant={agent.status === "active" ? "success" : "secondary"}
                  >
                    {agent.status}
                  </Badge>
                  <div className="text-xs text-muted-foreground mt-1">
                    {agent.entries} entries
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-primary mt-2" />
                  <div className="flex-1">
                    <div className="text-sm">{activity.action}</div>
                    <div className="text-xs text-muted-foreground">
                      {activity.agent} &middot; {activity.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-3 gap-4">
            <Button variant="outline" className="h-auto py-4 flex-col" asChild>
              <Link href="/dashboard/agents/new">
                <svg
                  className="w-6 h-6 mb-2"
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
              </Link>
            </Button>
            <Button variant="outline" className="h-auto py-4 flex-col" asChild>
              <Link href="/dashboard/api-keys">
                <svg
                  className="w-6 h-6 mb-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
                  />
                </svg>
                Generate API Key
              </Link>
            </Button>
            <Button variant="outline" className="h-auto py-4 flex-col" asChild>
              <Link href="/docs">
                <svg
                  className="w-6 h-6 mb-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
                View Docs
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
