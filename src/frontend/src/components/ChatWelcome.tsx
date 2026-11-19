export function ChatWelcome() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-3xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-2xl font-medium text-gray-900 mb-3">Ask about SeaTac airfield operations</h1>
        <p className="text-gray-600 text-sm max-w-2xl">
          Taxi times, runway use, delays and peak hours, from the Port's August 8, 2025 data.
        </p>
      </div>
    </div>
  );
}
