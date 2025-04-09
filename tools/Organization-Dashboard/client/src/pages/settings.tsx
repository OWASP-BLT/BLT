import { useState } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Bell, Shield, Lock, User, Globe, Send, Eye, PlusCircle } from "lucide-react";


export default function Settings() {
  const [activeTab, setActiveTab] = useState<string>("profile");
  const [emailNotifications, setEmailNotifications] = useState({
    securityAlerts: true,
    accountActivity: true,
    weeklyDigest: false,
    productUpdates: true,
    marketing: false
  });
  
  return (
      <div className="container px-4 py-6 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">Manage your account settings and preferences</p>
        </div>
        
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Settings Sidebar (Desktop) */}
          <Card className="hidden lg:block lg:col-span-3">
            <CardContent className="p-4">
              <nav className="space-y-1">
                <Button 
                  variant={activeTab === "profile" ? "default" : "ghost"} 
                  className="w-full justify-start"
                  onClick={() => setActiveTab("profile")}
                >
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </Button>
                
                <Button 
                  variant={activeTab === "security" ? "default" : "ghost"} 
                  className="w-full justify-start"
                  onClick={() => setActiveTab("security")}
                >
                  <Shield className="mr-2 h-4 w-4" />
                  Security
                </Button>
                
                <Button 
                  variant={activeTab === "notifications" ? "default" : "ghost"} 
                  className="w-full justify-start"
                  onClick={() => setActiveTab("notifications")}
                >
                  <Bell className="mr-2 h-4 w-4" />
                  Notifications
                </Button>
                
                <Button 
                  variant={activeTab === "access" ? "default" : "ghost"} 
                  className="w-full justify-start"
                  onClick={() => setActiveTab("access")}
                >
                  <Lock className="mr-2 h-4 w-4" />
                  Access
                </Button>
                
                <Button 
                  variant={activeTab === "api" ? "default" : "ghost"} 
                  className="w-full justify-start"
                  onClick={() => setActiveTab("api")}
                >
                  <Globe className="mr-2 h-4 w-4" />
                  API
                </Button>
              </nav>
            </CardContent>
          </Card>
          
          {/* Settings Tabs (Mobile) */}
          <div className="lg:hidden col-span-1">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid grid-cols-5 w-full">
                <TabsTrigger value="profile">
                  <User className="h-4 w-4 lg:mr-2" />
                  <span className="hidden sm:inline">Profile</span>
                </TabsTrigger>
                <TabsTrigger value="security">
                  <Shield className="h-4 w-4 lg:mr-2" />
                  <span className="hidden sm:inline">Security</span>
                </TabsTrigger>
                <TabsTrigger value="notifications">
                  <Bell className="h-4 w-4 lg:mr-2" />
                  <span className="hidden sm:inline">Notifications</span>
                </TabsTrigger>
                <TabsTrigger value="access">
                  <Lock className="h-4 w-4 lg:mr-2" />
                  <span className="hidden sm:inline">Access</span>
                </TabsTrigger>
                <TabsTrigger value="api">
                  <Globe className="h-4 w-4 lg:mr-2" />
                  <span className="hidden sm:inline">API</span>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          
          {/* Settings Content */}
          <div className="col-span-1 lg:col-span-9">
            {/* Profile Settings */}
            {activeTab === "profile" && (
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                  <CardDescription>Update your account details and public profile</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center space-x-4">
                      <Avatar className="h-20 w-20">
                        <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" />
                        <AvatarFallback>AU</AvatarFallback>
                      </Avatar>
                      <div className="space-y-1">
                        <h3 className="text-lg font-medium">Admin User</h3>
                        <p className="text-sm text-gray-500">Security Administrator</p>
                      </div>
                    </div>
                    <div className="mt-4 md:mt-0">
                      <Button variant="outline">Change Avatar</Button>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="fullName">Full Name</Label>
                      <Input id="fullName" defaultValue="Admin User" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="displayName">Display Name</Label>
                      <Input id="displayName" defaultValue="Admin" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input id="email" type="email" defaultValue="admin@example.com" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="role">Role</Label>
                      <Input id="role" defaultValue="Security Administrator" disabled />
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div>
                    <h3 className="text-lg font-medium mb-4">About</h3>
                    <div className="space-y-2">
                      <Label htmlFor="bio">Bio</Label>
                      <textarea
                        id="bio"
                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 h-32"
                        defaultValue="Security administrator with over 5 years of experience in vulnerability assessment and penetration testing."
                      />
                      <p className="text-sm text-gray-500">Brief description for your profile.</p>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="justify-end space-x-2">
                  <Button variant="outline">Cancel</Button>
                  <Button>Save Changes</Button>
                </CardFooter>
              </Card>
            )}
            
            {/* Security Settings */}
            {activeTab === "security" && (
              <Card>
                <CardHeader>
                  <CardTitle>Security Settings</CardTitle>
                  <CardDescription>Manage your account security and authentication</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">Password</h3>
                    <p className="text-sm text-gray-500">Change your password to maintain account security</p>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="currentPassword">Current Password</Label>
                        <Input id="currentPassword" type="password" />
                      </div>
                      <div></div>
                      <div className="space-y-2">
                        <Label htmlFor="newPassword">New Password</Label>
                        <Input id="newPassword" type="password" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="confirmPassword">Confirm Password</Label>
                        <Input id="confirmPassword" type="password" />
                      </div>
                    </div>
                    <div className="mt-4">
                      <Button>Update Password</Button>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">Two-Factor Authentication</h3>
                    <p className="text-sm text-gray-500">Add additional security with two-factor authentication</p>
                    <div className="flex items-center justify-between mt-4">
                      <div className="flex items-center">
                        <Shield className="h-8 w-8 text-blue-500 mr-3" />
                        <div>
                          <p className="font-medium">Two-Factor Authentication</p>
                          <p className="text-sm text-gray-500">Protect your account with 2FA</p>
                        </div>
                      </div>
                      <Button variant="outline">Enable</Button>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">Active Sessions</h3>
                    <p className="text-sm text-gray-500">Manage your active sessions across devices</p>
                    <div className="mt-4 space-y-4">
                      <div className="flex items-center justify-between border p-4 rounded-lg">
                        <div className="flex items-center">
                          <div className="mr-3 p-2 bg-blue-100 rounded-full">
                            <Eye className="h-5 w-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium">Current Session</p>
                            <p className="text-sm text-gray-500">Windows 10 • Chrome • IP: 192.168.1.1</p>
                          </div>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Active</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Notification Settings */}
            {activeTab === "notifications" && (
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                  <CardDescription>Manage how you receive notifications and updates</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Security Alerts</p>
                        <p className="text-sm text-gray-500">Receive notifications about security issues</p>
                      </div>
                      <Switch 
                        checked={emailNotifications.securityAlerts} 
                        onCheckedChange={(checked) => setEmailNotifications({...emailNotifications, securityAlerts: checked})}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Account Activity</p>
                        <p className="text-sm text-gray-500">Get notified about activity on your account</p>
                      </div>
                      <Switch 
                        checked={emailNotifications.accountActivity} 
                        onCheckedChange={(checked) => setEmailNotifications({...emailNotifications, accountActivity: checked})}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Weekly Digest</p>
                        <p className="text-sm text-gray-500">Weekly summary of security issues and bug reports</p>
                      </div>
                      <Switch 
                        checked={emailNotifications.weeklyDigest} 
                        onCheckedChange={(checked) => setEmailNotifications({...emailNotifications, weeklyDigest: checked})}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Product Updates</p>
                        <p className="text-sm text-gray-500">Notifications about new features and improvements</p>
                      </div>
                      <Switch 
                        checked={emailNotifications.productUpdates} 
                        onCheckedChange={(checked) => setEmailNotifications({...emailNotifications, productUpdates: checked})}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Marketing Communications</p>
                        <p className="text-sm text-gray-500">Receive product offers, news, and tips</p>
                      </div>
                      <Switch 
                        checked={emailNotifications.marketing} 
                        onCheckedChange={(checked) => setEmailNotifications({...emailNotifications, marketing: checked})}
                      />
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="justify-end space-x-2">
                  <Button variant="outline">Reset to Defaults</Button>
                  <Button>Save Preferences</Button>
                </CardFooter>
              </Card>
            )}
            
            {/* Access Settings */}
            {activeTab === "access" && (
              <Card>
                <CardHeader>
                  <CardTitle>Access Control</CardTitle>
                  <CardDescription>Manage access permissions and user roles</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">API Access</h3>
                    <p className="text-sm text-gray-500">Manage API access to the dashboard</p>
                    <div className="flex items-center justify-between mt-4">
                      <div className="flex items-center">
                        <Send className="h-8 w-8 text-blue-500 mr-3" />
                        <div>
                          <p className="font-medium">API Access</p>
                          <p className="text-sm text-gray-500">Allow applications to access dashboard data</p>
                        </div>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">Role Permissions</h3>
                    <p className="text-sm text-gray-500">Review your role permissions</p>
                    <div className="mt-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">View Security Issues</p>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Granted</Badge>
                      </div>
                      <Separator />
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Manage Bug Reports</p>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Granted</Badge>
                      </div>
                      <Separator />
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Invite Users</p>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Granted</Badge>
                      </div>
                      <Separator />
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Generate Reports</p>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Granted</Badge>
                      </div>
                      <Separator />
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Configure Settings</p>
                        </div>
                        <Badge className="bg-green-100 text-green-800">Granted</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* API Settings */}
            {activeTab === "api" && (
              <Card>
                <CardHeader>
                  <CardTitle>API Configuration</CardTitle>
                  <CardDescription>Manage your API keys and webhook endpoints</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">API Keys</h3>
                    <p className="text-sm text-gray-500">Manage keys for third-party applications</p>
                    <div className="mt-4 space-y-4">
                      <div className="flex items-center justify-between border p-4 rounded-lg">
                        <div>
                          <p className="font-medium">Production API Key</p>
                          <p className="text-sm font-mono text-gray-500">sk_prod_****************XXXX</p>
                          <div className="mt-1">
                            <Badge variant="outline">Created 3 months ago</Badge>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <Button variant="outline" size="sm">Reveal</Button>
                          <Button variant="outline" size="sm" className="text-red-500 hover:text-red-600">Revoke</Button>
                        </div>
                      </div>
                      <div className="flex items-center justify-between border p-4 rounded-lg">
                        <div>
                          <p className="font-medium">Development API Key</p>
                          <p className="text-sm font-mono text-gray-500">sk_dev_****************YYYY</p>
                          <div className="mt-1">
                            <Badge variant="outline">Created 5 months ago</Badge>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <Button variant="outline" size="sm">Reveal</Button>
                          <Button variant="outline" size="sm" className="text-red-500 hover:text-red-600">Revoke</Button>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4">
                      <Button className="flex items-center gap-2">
                        <PlusCircle className="h-4 w-4" />
                        <span>Generate New API Key</span>
                      </Button>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">Webhook Endpoints</h3>
                    <p className="text-sm text-gray-500">Configure webhooks for real-time events</p>
                    <div className="grid grid-cols-1 gap-4 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="webhookUrl">Webhook URL</Label>
                        <Input id="webhookUrl" placeholder="https://your-app.com/webhook" />
                      </div>
                      <div className="space-y-2">
                        <Label>Events to notify</Label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                          <div className="flex items-center space-x-2">
                            <Checkbox id="securityEvents" />
                            <label htmlFor="securityEvents" className="text-sm">Security Events</label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Checkbox id="bugEvents" />
                            <label htmlFor="bugEvents" className="text-sm">Bug Events</label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Checkbox id="userEvents" />
                            <label htmlFor="userEvents" className="text-sm">User Events</label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Checkbox id="systemEvents" />
                            <label htmlFor="systemEvents" className="text-sm">System Events</label>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4">
                      <Button>Save Webhook</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
  );
}