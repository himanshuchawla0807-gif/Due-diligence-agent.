import { useState, useRef } from 'react';
import { API_BASE_URL } from '@/config';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, FileText, CheckCircle, AlertCircle, ArrowLeft, Rocket, Briefcase, Building2 } from 'lucide-react';
import { CanvasRevealEffect } from './canvas-reveal-effect';

// Supported industry types
type IndustryType = 'VC' | 'PE' | 'FO' | 'MA' | 'CA' | 'OTHER' | null;

interface UploadAnalysisResult {
  response?: string;
  citations?: any[];
  steps?: any[];
  findings?: any[];
}

interface FileUploadZoneProps {
  onUploadComplete: (files: File[], sessionId: string, industry: IndustryType, analysis?: UploadAnalysisResult) => void;
  onSessionCreated?: (sessionId: string) => void;  // ✅ NEW: Notify parent when session is created for URL update
  // Industry passed from URL params (from user profile)
  initialIndustry?: IndustryType;
  customIndustry?: string;
  userId?: string | null;     // ✅ NEW: User ID for auth
  serviceKey?: string; // ✅ NEW: Service Key for auth override
}

interface FileObject {
  id: string;
  file: File;
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  relativePath?: string;
}

export function FileUploadZone({ onUploadComplete, onSessionCreated, initialIndustry, customIndustry, userId, serviceKey }: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileObject[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  // Use initialIndustry if provided (from user profile), otherwise null for picker
  const [selectedIndustry, setSelectedIndustry] = useState<IndustryType>(initialIndustry || null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Log custom industry for OTHER type (will be used by backend)
  if (initialIndustry === 'OTHER' && customIndustry) {
    console.log('[DD] Custom industry from user profile:', customIndustry);
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelection(e.dataTransfer.files);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileSelection(e.target.files);
    }
  };

  const handleFileSelection = async (files: FileList) => {
    if (files.length === 0) return;

    const filesArray = Array.from(files);
    let currentSessionId = sessionId;
    let firstFileUploaded = false;

    if (!currentSessionId) {
      const firstFile = filesArray[0];
      const formData = new FormData();
      const relativePath = (firstFile as any).webkitRelativePath || firstFile.name;
      const fileToUpload = new File([firstFile], relativePath, { type: firstFile.type });

      formData.append('files', fileToUpload);
      formData.append('auto_process', 'false');

      // ✅ NEW: Add user_id to form (for trusted backend storage)
      if (userId) {
        formData.append('user_id', userId);
      }
      formData.append('file_path', relativePath);

      try {
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
          method: 'POST',
          headers: {
            // ✅ NEW: Send Service Key for trust
            'x-service-key': serviceKey || '',
          },
          body: formData,
        });
        const data = await response.json();
        currentSessionId = data.session_id;
        setSessionId(currentSessionId);
        firstFileUploaded = true;

        // ✅ NEW: Notify parent immediately for URL update
        if (onSessionCreated && currentSessionId) {
          onSessionCreated(currentSessionId);
        }

        const firstFileObj: FileObject = {
          id: Date.now() + Math.random().toString(),
          file: firstFile,
          name: firstFile.name,
          size: firstFile.size,
          status: 'success',
          progress: 100,
          relativePath: relativePath
        };
        setSelectedFiles(prev => [...prev, firstFileObj]);
      } catch (error) {
        console.error('[SESSION ERROR]', error);
        return;
      }
    }

    const filesToUpload = firstFileUploaded ? filesArray.slice(1) : filesArray;
    const totalFiles = filesToUpload.length;
    const uploadTracker = { completed: 0 };

    if (firstFileUploaded && totalFiles === 0) {
      triggerIndustryAnalysis(currentSessionId!, filesArray);
      return;
    }

    filesToUpload.forEach((file) => {
      const relativePath = (file as any).webkitRelativePath || file.name;
      const fileObj: FileObject = {
        id: Date.now() + Math.random().toString(),
        file: file,
        name: file.name,
        size: file.size,
        status: 'pending',
        progress: 0,
        relativePath: relativePath
      };
      setSelectedFiles(prev => [...prev, fileObj]);

      uploadFile(fileObj, currentSessionId!, () => {
        uploadTracker.completed++;
        if (uploadTracker.completed === totalFiles) {
          triggerIndustryAnalysis(currentSessionId!, filesArray);
        }
      });
    });
  };

  const triggerIndustryAnalysis = (currentSessionId: string, filesArray: File[]) => {
    if (!currentSessionId) {
      console.error('[INDUSTRY_DD] Cannot start analysis: Session ID is missing');
      return;
    }

    console.log(`[INDUSTRY_DD] Starting ${selectedIndustry} analysis for session ${currentSessionId}...`);
    setTimeout(() => {
      fetch(`${API_BASE_URL}/api/industry-dd`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          industry: selectedIndustry,
          query: 'Generate comprehensive due diligence report',
          user_id: userId || 'default-user'  // ✅ CRITICAL: Pass user_id for Firebase fallback
        })
      })
        .then(res => {
          if (!res.ok) throw new Error(`Server responded with ${res.status}`);
          return res.json();
        })
        .then(data => {
          console.log(`[INDUSTRY_DD] Started:`, data);
          onUploadComplete(filesArray, currentSessionId, selectedIndustry, {
            response: data.response,
            citations: data.citations || [],
            steps: data.steps || [],
            findings: data.findings || []
          });
        })
        .catch(err => {
          console.error(`[INDUSTRY_DD] Failed:`, err);
          // Still complete upload so user isn't stuck, but show error state if possible
          onUploadComplete(filesArray, currentSessionId, selectedIndustry);
        });
    }, 800);
  };

  const uploadFile = async (fileObj: FileObject, useSessionId: string, onComplete?: () => void) => {
    setSelectedFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'uploading' } : f));

    try {
      // Assuming userId and serviceKey are available, but need to be passed as props...
      // Wait, I need to update interface first.

      // ... inside uploadFile function
      const formData = new FormData();
      const uploadPath = fileObj.relativePath || fileObj.file.name;
      const fileToUpload = new File([fileObj.file], uploadPath, { type: fileObj.file.type });

      formData.append('files', fileToUpload);
      formData.append('session_id', useSessionId);
      formData.append('auto_process', 'false');

      // ✅ NEW: Add user_id to form (for trusted backend storage)
      if (userId) {
        formData.append('user_id', userId);
      }

      // ✅ NEW: Send explicit file path to preserve folder structure
      // Browsers often flatten filenames in multipart upload, so we send this separately
      formData.append('file_path', uploadPath);

      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        headers: {
          // ✅ NEW: Send Service Key for trust
          'x-service-key': serviceKey || '',
        },
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }

      setSelectedFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'success', progress: 100 } : f));
      if (onComplete) onComplete();

    } catch (error) {
      console.error('[UPLOAD ERROR]', error);
      setSelectedFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'error' } : f));
      if (onComplete) onComplete();
    }
  };

  const removeFile = (fileId: string) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen w-full bg-[#F5F5F7] text-[#1D1D1F] font-sans selection:bg-gray-200 overflow-hidden relative">
      <div className="max-w-7xl mx-auto px-6 py-20 relative z-10">

        <AnimatePresence mode="wait">
          {!selectedIndustry ? (
            <motion.div
              key="industry-selection"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col items-center"
            >
              <div className="text-center mb-24">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1, duration: 0.5 }}
                  className="inline-block mb-6 px-4 py-1.5 rounded-full bg-white border border-gray-200 shadow-sm text-sm font-medium text-gray-500"
                >
                  Due Diligence Agent
                </motion.div>
                <motion.h1
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-6xl font-semibold tracking-tight mb-6 text-gray-900"
                >
                  Select Industry Focus
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="text-xl text-gray-500 font-light max-w-2xl mx-auto leading-relaxed"
                >
                  Choose your investment focus to initialize specialized AI agents optimized for deep vertical analysis.
                </motion.p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-6xl mx-auto">
                {[
                  {
                    id: 'VC',
                    Icon: Rocket,
                    title: 'Venture Capital',
                    desc: 'Early-stage startups',
                    details: ['Growth & Traction', 'TAM/SAM Analysis', 'Team Assessment'],
                    colors: [[16, 185, 129]] // Emerald Green
                  },
                  {
                    id: 'PE',
                    Icon: Briefcase,
                    title: 'Private Equity',
                    desc: 'Mature companies',
                    details: ['EBITDA Analysis', 'Operations Review', 'Value Creation'],
                    colors: [[100, 116, 139]] // Slate Gray - different from CA
                  },
                  {
                    id: 'FO',
                    Icon: Building2,
                    title: 'Family Office',
                    desc: 'Long-term investments',
                    details: ['ESG & Impact', 'Values Alignment', 'Legacy Planning'],
                    colors: [[59, 130, 246]] // Blue
                  },
                  {
                    id: 'MA',
                    Icon: Briefcase,
                    title: 'M&A Advisory',
                    desc: 'Mergers & acquisitions',
                    details: ['Deal Structure', 'Synergy Analysis', 'Integration Risk'],
                    colors: [[124, 58, 237]] // Deep Violet Purple
                  },
                  {
                    id: 'CA',
                    Icon: Building2,
                    title: 'Chartered Accountancy',
                    desc: 'Audit & compliance',
                    details: ['Audit Findings', 'Tax Analysis', 'Compliance Review'],
                    colors: [[245, 158, 11]] // Amber
                  },
                  {
                    id: 'OTHER',
                    Icon: Briefcase,
                    title: 'Other',
                    desc: 'Custom industry',
                    details: ['Flexible Analysis', 'Adaptive Approach', 'Custom Focus'],
                    colors: [[107, 114, 128]] // Gray
                  }
                ].map((item, index) => (
                  <Card
                    key={item.id}
                    title={item.title}
                    icon={<item.Icon className="w-10 h-10 text-gray-900" strokeWidth={1.5} />}
                    description={item.desc}
                    details={item.details}
                    onClick={() => setSelectedIndustry(item.id as any)}
                    index={index}
                  >
                    <CanvasRevealEffect
                      animationSpeed={3}
                      containerClassName="bg-black"
                      colors={item.colors}
                      dotSize={2}
                    />
                  </Card>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="upload-zone"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-4xl mx-auto"
            >
              <div className="flex items-center justify-between mb-10">
                {/* Only show Back to Selection if industry wasn't pre-set from URL params (profile) */}
                {!initialIndustry ? (
                  <button
                    onClick={() => {
                      setSelectedIndustry(null);
                      setSelectedFiles([]);
                    }}
                    className="group flex items-center text-gray-500 hover:text-gray-900 transition-colors font-medium px-4 py-2 rounded-full hover:bg-white"
                  >
                    <ArrowLeft className="w-5 h-5 mr-2 group-hover:-translate-x-1 transition-transform" />
                    Back to Selection
                  </button>
                ) : (
                  <div /> // Empty placeholder for flex spacing
                )}

                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="px-6 py-2.5 bg-white rounded-full shadow-sm border border-gray-100 flex items-center"
                >
                  <span className={`w-2 h-2 rounded-full mr-3 animate-pulse ${selectedIndustry === 'VC' ? 'bg-emerald-500' :
                    selectedIndustry === 'PE' ? 'bg-slate-500' :
                      selectedIndustry === 'FO' ? 'bg-blue-500' :
                        selectedIndustry === 'MA' ? 'bg-violet-600' :
                          selectedIndustry === 'CA' ? 'bg-amber-500' :
                            'bg-gray-500'
                    }`} />
                  <span className="text-sm font-semibold text-gray-700">
                    {selectedIndustry === 'VC' ? 'Venture Capital' :
                      selectedIndustry === 'PE' ? 'Private Equity' :
                        selectedIndustry === 'FO' ? 'Family Office' :
                          selectedIndustry === 'MA' ? 'M&A Advisory' :
                            selectedIndustry === 'CA' ? 'Chartered Accountancy' :
                              'Other'}
                  </span>
                </motion.div>
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  relative group cursor-pointer overflow-hidden
                  bg-white rounded-[2.5rem] border border-gray-200 transition-all duration-500
                  ${isDragging
                    ? 'border-gray-400 bg-gray-50 scale-[1.02] shadow-2xl'
                    : 'hover:border-gray-300 hover:shadow-xl'
                  }
                `}
              >
                {/* CanvasRevealEffect removed from upload zone as requested */}

                <div className="py-32 px-8 text-center relative z-10">
                  <div className={`
                    w-24 h-24 mx-auto rounded-3xl flex items-center justify-center mb-8
                    bg-gray-50 border border-gray-100
                    group-hover:scale-110 group-hover:rotate-3 transition-all duration-500
                  `}>
                    <Upload className="w-10 h-10 text-gray-900" strokeWidth={1.5} />
                  </div>
                  <h2 className="text-4xl font-semibold text-gray-900 mb-4 tracking-tight">
                    Upload Documents
                  </h2>
                  <p className="text-lg text-gray-500 max-w-md mx-auto mb-10 font-light leading-relaxed">
                    Drag and drop your files here, or click to browse. <br />
                    We support PDF, Excel, and Word documents.
                  </p>
                  <button className="px-10 py-4 bg-black text-white rounded-full font-medium hover:bg-gray-800 transition-all hover:shadow-lg hover:-translate-y-1 active:translate-y-0">
                    Choose Files
                  </button>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                  accept="*/*"
                  {...({ webkitdirectory: "", directory: "", mozdirectory: "" } as any)}
                />
              </div>

              {selectedFiles.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="mt-16"
                >
                  <h3 className="text-xl font-semibold mb-6 text-gray-900 pl-4">Selected Files</h3>
                  <div className="space-y-4">
                    <AnimatePresence>
                      {selectedFiles.map((file, index) => (
                        <motion.div
                          key={file.id}
                          initial={{ opacity: 0, x: -20, y: 20 }}
                          animate={{ opacity: 1, x: 0, y: 0 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ delay: index * 0.1 }}
                          className="group flex items-center justify-between p-5 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all"
                        >
                          <div className="flex items-center flex-1 min-w-0">
                            <div className="w-12 h-12 rounded-2xl bg-gray-50 flex items-center justify-center mr-5 text-gray-500 border border-gray-100">
                              <FileText className="w-6 h-6" strokeWidth={1.5} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-2">
                                <p className="font-medium text-gray-900 truncate pr-4 text-lg">{file.name}</p>
                                <span className="text-sm text-gray-400 whitespace-nowrap font-medium bg-gray-50 px-2 py-1 rounded-lg">{formatFileSize(file.size)}</span>
                              </div>
                              {file.status === 'uploading' && (
                                <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                  <motion.div
                                    className="h-full bg-gray-900"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${file.progress}%` }}
                                  />
                                </div>
                              )}
                              {file.status === 'success' && (
                                <motion.span
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  className="text-sm text-emerald-600 flex items-center font-medium"
                                >
                                  <CheckCircle className="w-4 h-4 mr-1.5" /> Ready for analysis
                                </motion.span>
                              )}
                              {file.status === 'error' && (
                                <span className="text-sm text-red-500 flex items-center font-medium">
                                  <AlertCircle className="w-4 h-4 mr-1.5" /> Upload failed
                                </span>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(file.id)}
                            className="ml-6 p-3 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

const Card = ({
  title,
  icon,
  children,
  description,
  details,
  onClick,
  index
}: {
  title: string;
  icon: React.ReactNode;
  children?: React.ReactNode;
  description: string;
  details: string[];
  onClick: () => void;
  index: number;
}) => {
  const [hovered, setHovered] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 * (index + 1), duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onClick}
      className="border border-gray-200 group/canvas-card flex flex-col items-start justify-between bg-white w-full mx-auto p-8 relative h-[28rem] rounded-[2.5rem] overflow-hidden cursor-pointer hover:shadow-2xl transition-all duration-500"
    >
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full w-full absolute inset-0"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-20 w-full h-full flex flex-col justify-between pointer-events-none">
        <div>
          <div className="w-20 h-20 rounded-2xl bg-gray-50 flex items-center justify-center mb-8 border border-gray-100 group-hover/canvas-card:bg-white/80 group-hover/canvas-card:backdrop-blur-sm transition-colors">
            {icon}
          </div>
          <h2 className="text-3xl font-semibold text-gray-900 mb-3 group-hover/canvas-card:text-white transition-colors duration-200">
            {title}
          </h2>
          <p className="text-lg text-gray-500 font-medium group-hover/canvas-card:text-white/80 transition-colors duration-200">
            {description}
          </p>
        </div>

        <div className="space-y-2 opacity-0 group-hover/canvas-card:opacity-100 transition-opacity duration-500 transform translate-y-4 group-hover/canvas-card:translate-y-0">
          {details.map((detail, i) => (
            <div key={i} className="flex items-center text-sm text-white/90">
              <div className="w-1.5 h-1.5 rounded-full bg-white mr-3" />
              {detail}
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};
