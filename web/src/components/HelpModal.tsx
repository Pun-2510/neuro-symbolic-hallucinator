import { useState } from 'react';
import { HelpCircle, X, Keyboard, Upload, FileText, AlertTriangle, CheckCircle, BookOpen } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const [activeSection, setActiveSection] = useState<string>('overview');

  if (!isOpen) return null;

  const sections = [
    { id: 'overview', label: 'Overview', icon: BookOpen },
    { id: 'getting-started', label: 'Getting Started', icon: Upload },
    { id: 'verdicts', label: 'Understanding Verdicts', icon: AlertTriangle },
    { id: 'keyboard', label: 'Keyboard Shortcuts', icon: Keyboard },
  ];

  const shortcuts = [
    { keys: ['Ctrl', 'U'], description: 'Upload new essay' },
    { keys: ['Ctrl', '/'], description: 'Open this help' },
    { keys: ['Esc'], description: 'Close dialogs/modals' },
    { keys: ['Ctrl', 'D'], description: 'Toggle dark mode' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex">
        {/* Sidebar */}
        <div className="w-56 bg-slate-50 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-semibold text-slate-900 dark:text-white">Help</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          <nav className="space-y-1">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeSection === section.id
                      ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {section.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeSection === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
                  Welcome to Essay Integrity Checker
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  This tool helps verify the integrity of citations in academic essays.
                  It checks if cited references actually exist and match the provided metadata.
                </p>
              </div>

              <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-indigo-900 dark:text-indigo-300">
                      Decision Support Tool
                    </p>
                    <p className="text-sm text-indigo-700 dark:text-indigo-400 mt-1">
                      This system provides analysis to assist expert review.
                      Final judgment on citation integrity requires human expertise.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-slate-900 dark:text-white mb-2">How it works:</h4>
                <ol className="space-y-2 text-slate-600 dark:text-slate-400 list-decimal list-inside">
                  <li>Upload your essay (PDF format)</li>
                  <li>System extracts and analyzes citations</li>
                  <li>Each citation is verified against academic databases</li>
                  <li>View results with detailed verdicts and CIS score</li>
                  <li>Export report in JSON, CSV, PDF, or DOCX format</li>
                </ol>
              </div>
            </div>
          )}

          {activeSection === 'getting-started' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Getting Started
              </h3>

              <div className="space-y-4">
                <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 text-white rounded-full text-sm font-bold shrink-0">
                    1
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-white">Upload Your Essay</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      Go to the Upload page and drag & drop your PDF file, or click to select it.
                      The system accepts PDF files up to 50MB.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 text-white rounded-full text-sm font-bold shrink-0">
                    2
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-white">Wait for Analysis</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      The analysis typically takes 30-60 seconds depending on the essay length.
                      You can monitor progress in real-time.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 text-white rounded-full text-sm font-bold shrink-0">
                    3
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-white">Review Results</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      View the Citation Integrity Score (CIS) and examine individual citation verdicts.
                      Click on any citation for detailed information.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 text-white rounded-full text-sm font-bold shrink-0">
                    4
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-white">Export Report</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      Download your analysis report in JSON, CSV, PDF, or DOCX format for documentation or further review.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'verdicts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Understanding Verdicts
              </h3>

              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    <h4 className="font-medium text-emerald-900 dark:text-emerald-300">VERIFIED</h4>
                  </div>
                  <p className="text-sm text-emerald-700 dark:text-emerald-400">
                    Citation verified successfully through academic databases. The reference exists and metadata matches.
                  </p>
                </div>

                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    <h4 className="font-medium text-amber-900 dark:text-amber-300">METADATA_ERROR</h4>
                  </div>
                  <p className="text-sm text-amber-700 dark:text-amber-400">
                    Citation found but metadata (author, title, year, venue) doesn't match the database record.
                  </p>
                </div>

                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                    <h4 className="font-medium text-red-900 dark:text-red-300">SUSPECTED_HALLUCINATION</h4>
                  </div>
                  <p className="text-sm text-red-700 dark:text-red-400">
                    Citation appears to be fabricated or doesn't exist in any academic database.
                    This may indicate an integrity issue.
                  </p>
                </div>

                <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-300 dark:border-slate-700">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                    <h4 className="font-medium text-slate-900 dark:text-slate-300">UNRESOLVED</h4>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Insufficient evidence to determine citation validity. Manual review recommended.
                  </p>
                </div>

                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    <h4 className="font-medium text-purple-900 dark:text-purple-300">RESOURCE</h4>
                  </div>
                  <p className="text-sm text-purple-700 dark:text-purple-400">
                    Citation is a URL/web resource. Not verified through academic databases.
                  </p>
                </div>
              </div>

              <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 mt-6">
                <h4 className="font-medium text-slate-900 dark:text-white mb-2">CIS Score</h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  The Citation Integrity Score (CIS) is a composite metric (0-100%) indicating the overall integrity
                  of citations in your essay. Higher scores indicate better citation integrity.
                </p>
              </div>
            </div>
          )}

          {activeSection === 'keyboard' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Keyboard Shortcuts
              </h3>

              <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                  Use these shortcuts for faster navigation:
                </p>

                <div className="space-y-3">
                  {shortcuts.map((shortcut, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-slate-600 dark:text-slate-400">{shortcut.description}</span>
                      <div className="flex items-center gap-1">
                        {shortcut.keys.map((key, keyIndex) => (
                          <span key={keyIndex}>
                            <kbd className="px-2 py-1 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded text-xs font-mono text-slate-700 dark:text-slate-300">
                              {key}
                            </kbd>
                            {keyIndex < shortcut.keys.length - 1 && (
                              <span className="text-slate-400 mx-1">+</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
