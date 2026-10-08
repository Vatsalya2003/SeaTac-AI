import { ImageWithFallback } from "./figma/ImageWithFallback";

export function ChatWelcome() {
  const sampleQuestions = [
    "How do I troubleshoot gate access issues?",
    "What are the security protocols for visitor access?",
    "How can I generate weekly access reports?",
    "What should I do if the gate won't respond?",
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-3xl mx-auto">
      {/* Logo */}
      <div className="mb-8">
        <ImageWithFallback
          src="/aiportlogo.png"
          alt="Gate Assistant Logo"
          className="w-[40px] h-auto sm:w-[60px] md:w-[80px] lg:w-[100px] object-contain"
        />
      </div>

      {/* Welcome Message */}
      <div className="text-center mb-12">
        <h1 className="text-2xl font-medium text-gray-900 mb-3">
          Hello! How can I assist with your gate queries today?
        </h1>
        <p className="text-gray-600 text-sm max-w-2xl">
          {"I'm here to help with gate assignments, flight gate changes, and\u00A0more."}
        </p>
      </div>
    </div>
  );
}