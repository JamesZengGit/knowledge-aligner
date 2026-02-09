'use client';

import { useState } from 'react';
import { User, Settings, Search } from 'lucide-react';

interface HeaderProps {
  currentUser: {
    user_name: string;
    role: string;
    user_id: string;
  };
  accounts?: {
    [key: string]: {
      user_id: string;
      user_name: string;
      role: string;
      owned_components: string[];
    };
  };
  currentAccount?: string;
  onAccountChange?: (accountId: string) => void;
}

export function Header({ currentUser, accounts, currentAccount, onAccountChange }: HeaderProps) {
  const [showAccountSwitch, setShowAccountSwitch] = useState(false);

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">HD</span>
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                Hardware Digest
              </h1>
              <p className="text-sm text-gray-500">
                AI-Powered Decision Tracking
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search decisions..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>


          {/* Settings */}
          <button className="p-2 text-gray-400 hover:text-gray-600">
            <Settings className="w-5 h-5" />
          </button>

          {/* User Profile with Account Switching */}
          <div className="flex items-center space-x-3 pl-4 border-l border-gray-200 relative">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">
                {currentUser.user_name}
              </p>
              <p className="text-xs text-gray-500">
                {currentUser.role}
              </p>
            </div>
            <button
              onClick={() => setShowAccountSwitch(!showAccountSwitch)}
              className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors"
            >
              <User className="w-4 h-4 text-gray-600" />
            </button>

            {/* Account Switcher Dropdown */}
            {showAccountSwitch && accounts && onAccountChange && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="p-2">
                  <p className="text-xs text-gray-500 px-3 py-2 font-medium uppercase tracking-wide">
                    Switch Account
                  </p>
                  {Object.entries(accounts).map(([accountId, account]) => (
                    <button
                      key={accountId}
                      onClick={() => {
                        onAccountChange(accountId);
                        setShowAccountSwitch(false);
                      }}
                      className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left hover:bg-gray-50 transition-colors ${
                        currentAccount === accountId ? 'bg-blue-50 border-blue-200' : ''
                      }`}
                    >
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                        account.role === 'Mechanical Lead' ? 'bg-green-100 text-green-700' :
                        account.role === 'Firmware Engineer' ? 'bg-blue-100 text-blue-700' :
                        'bg-orange-100 text-orange-700'
                      }`}>
                        {account.user_name[0]}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {account.user_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {account.role}
                        </p>
                      </div>
                      {currentAccount === accountId && (
                        <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}