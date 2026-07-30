import { useEffect, useRef, useState } from "react";
import { Paperclip, Mic, Camera, X, Loader2, FileText, Square } from "lucide-react";
import { uploadFile } from "../api/client";
import { useSpeechToText } from "../hooks/useVoice";

const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp";
const FILE_ACCEPT = ".pdf,.txt,.md,.csv,.json,.docx,.py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.go,.rs,.rb,.php,.html,.css,.yaml,.yml,.sh,.sql";

/**
 * Multimodal prompt composer: text, file attach, image attach, and
 * browser-native voice dictation, all feeding one `onSubmit` call.
 *
 * Attaching a file/image immediately POSTs it to /api/upload (via
 * uploadFile) to get extracted text or a base64 payload ready to send with
 * the next query, and shows a preview chip above the input bar. Voice
 * input uses the Web Speech API (useSpeechToText) — no backend involved
 * until the resulting text is submitted like any typed prompt.
 *
 * @param {Object} props
 * @param {(payload: {text: string, attachment: Object|null}) => void} props.onSubmit
 *   Called with the composed prompt text and any attachment when the user sends.
 * @param {boolean} props.disabled - Disables all input while a query is in flight.
 * @param {string} [props.prefill] - Text to drop into the composer (e.g. a clicked
 *   suggestion chip). Applied whenever `prefillKey` changes, not on every render.
 * @param {*} [props.prefillKey] - Any value whose identity change re-applies `prefill`.
 * @returns {JSX.Element}
 */
export default function ChatInput({ onSubmit, disabled, prefill, prefillKey }) {
  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState(null); // { kind, filename, ... }
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const textareaRef = useRef(null);

  const { supported: voiceSupported, listening, start, stop } = useSpeechToText({
    onResult: (transcript, isFinal) => {
      setText(transcript);
      if (isFinal) textareaRef.current?.focus();
    },
  });

  useEffect(() => {
    if (prefillKey == null) return;
    setText(prefill || "");
    textareaRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillKey]);

  const handlePick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("File exceeds the 10MB limit");
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      const data = await uploadFile(file);
      setAttachment(data);
    } catch (err) {
      setUploadError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const submit = () => {
    if (disabled || uploading) return;
    if (!text.trim() && !attachment) return;
    onSubmit({ text: text.trim(), attachment });
    setText("");
    setAttachment(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {uploadError && <div className="text-xs" style={{ color: "var(--status-critical)" }}>{uploadError}</div>}

      {attachment && (
        <div
          className="flex items-center gap-2 self-start border px-3 py-2 text-sm"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          {attachment.kind === "image" ? (
            <img
              src={`data:${attachment.mime_type};base64,${attachment.data_base64}`}
              alt={attachment.filename}
              className="h-10 w-10 rounded object-cover"
            />
          ) : (
            <FileText size={18} style={{ color: "var(--text-muted)" }} />
          )}
          <div className="min-w-0">
            <div className="truncate font-medium" style={{ color: "var(--text-primary)" }}>
              {attachment.filename}
            </div>
            {attachment.preview && (
              <div className="max-w-xs truncate text-xs" style={{ color: "var(--text-muted)" }}>
                {attachment.preview}
              </div>
            )}
          </div>
          <button onClick={() => setAttachment(null)} className="ml-1 shrink-0" style={{ color: "var(--text-muted)" }}>
            <X size={14} />
          </button>
        </div>
      )}

      <div
        className="flex w-full items-end gap-2 border p-2"
        style={{ borderColor: "var(--border-strong)", background: "var(--surface-2)" }}
      >
        <input ref={fileInputRef} type="file" accept={FILE_ACCEPT} className="hidden" onChange={handlePick} />
        <input ref={imageInputRef} type="file" accept={IMAGE_ACCEPT} className="hidden" onChange={handlePick} />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || uploading}
          title="Attach a document"
          className="flex h-9 w-9 shrink-0 items-center justify-center opacity-70 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100 disabled:opacity-40"
          style={{ color: "var(--text-secondary)" }}
        >
          <Paperclip size={18} />
        </button>

        <button
          type="button"
          onClick={() => imageInputRef.current?.click()}
          disabled={disabled || uploading}
          title="Attach an image"
          className="flex h-9 w-9 shrink-0 items-center justify-center opacity-70 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100 disabled:opacity-40"
          style={{ color: "var(--text-secondary)" }}
        >
          <Camera size={18} />
        </button>

        {voiceSupported && (
          <button
            type="button"
            onClick={() => (listening ? stop() : start())}
            disabled={disabled}
            title={listening ? "Stop listening" : "Speak your prompt"}
            className={`flex h-9 w-9 shrink-0 items-center justify-center border transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100 disabled:opacity-40 ${listening ? "opacity-100" : "opacity-70"}`}
            style={{
              color: listening ? "var(--status-critical)" : "var(--text-secondary)",
              borderColor: listening ? "var(--status-critical)" : "transparent",
            }}
          >
            {listening ? <Square size={14} /> : <Mic size={18} />}
          </button>
        )}

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={listening ? "Listening..." : "Ask all agents anything..."}
          rows={1}
          disabled={disabled}
          className="max-h-40 min-h-[36px] flex-1 resize-none bg-transparent px-1 py-1.5 text-sm outline-none placeholder:text-[var(--text-muted)]"
          style={{ color: "var(--text-primary)" }}
        />

        <button
          type="button"
          onClick={submit}
          disabled={disabled || uploading || (!text.trim() && !attachment)}
          className="flex h-9 shrink-0 items-center justify-center gap-1.5 border px-3.5 opacity-60 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100 disabled:opacity-30 disabled:hover:opacity-30"
          style={{ borderColor: "var(--text-primary)", color: "var(--text-primary)" }}
        >
          {uploading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <span className="text-2xs uppercase" style={{ letterSpacing: "var(--tracking-label)" }}>
              Run
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
