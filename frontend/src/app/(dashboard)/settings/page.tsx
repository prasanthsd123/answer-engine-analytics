"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/lib/api";

export default function SettingsPage() {
  const { data: user } = useQuery({
    queryKey: ["user"],
    queryFn: authApi.getMe,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    // Simulate save - in real app, this would call an API
    setTimeout(() => {
      setSaving(false);
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
    }, 1000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600">Manage your account and application settings</p>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {message.text}
        </div>
      )}

      {/* Profile Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
            />
            <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name
            </label>
            <input
              type="text"
              defaultValue={user?.full_name || ''}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Enter your full name"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      {/* Notification Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Notifications</h2>
        <div className="space-y-4">
          <label className="flex items-center">
            <input type="checkbox" defaultChecked className="rounded text-primary-600 focus:ring-primary-500" />
            <span className="ml-2 text-gray-700">Email notifications for analysis completion</span>
          </label>
          <label className="flex items-center">
            <input type="checkbox" defaultChecked className="rounded text-primary-600 focus:ring-primary-500" />
            <span className="ml-2 text-gray-700">Weekly brand visibility reports</span>
          </label>
          <label className="flex items-center">
            <input type="checkbox" className="rounded text-primary-600 focus:ring-primary-500" />
            <span className="ml-2 text-gray-700">Marketing and product updates</span>
          </label>
        </div>
      </div>

      {/* API Keys Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h2>
        <p className="text-gray-600 mb-4">
          API keys are managed server-side for security. Contact your administrator to update API configurations.
        </p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">OpenAI:</span>
            <span className="ml-2 text-green-600">Configured</span>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">Perplexity:</span>
            <span className="ml-2 text-green-600">Configured</span>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">Anthropic:</span>
            <span className="ml-2 text-gray-400">Not configured</span>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">Google AI:</span>
            <span className="ml-2 text-gray-400">Not configured</span>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-white rounded-lg shadow p-6 border border-red-200">
        <h2 className="text-lg font-semibold text-red-600 mb-4">Danger Zone</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Delete all analysis data</p>
              <p className="text-sm text-gray-500">This will permanently delete all your analysis history</p>
            </div>
            <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">
              Delete Data
            </button>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Delete account</p>
              <p className="text-sm text-gray-500">Permanently delete your account and all associated data</p>
            </div>
            <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
