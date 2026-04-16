import { ContentBlock } from "@langchain/core/messages";
import { toast } from "sonner";

export function normalizeUploadMimeType(file: Pick<File, "type" | "name">): string {
  if (file.type) {
    return file.type;
  }

  const lowered = file.name.toLowerCase();
  if (lowered.endsWith(".md")) return "text/markdown";
  if (lowered.endsWith(".txt")) return "text/plain";
  if (lowered.endsWith(".pdf")) return "application/pdf";
  return "";
}

// Returns a Promise of a typed multimodal block for images or supported files.
export async function fileToContentBlock(
  file: File,
): Promise<ContentBlock.Multimodal.Data> {
  const supportedImageTypes = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
  ];
  const supportedFileTypes = [
    ...supportedImageTypes,
    "application/pdf",
    "text/markdown",
    "text/plain",
  ];

  const mimeType = normalizeUploadMimeType(file);

  if (!supportedFileTypes.includes(mimeType)) {
    toast.error(
      `Unsupported file type: ${mimeType || file.name}. Supported types are: ${supportedFileTypes.join(", ")}`,
    );
    return Promise.reject(new Error(`Unsupported file type: ${mimeType || file.name}`));
  }

  const data = await fileToBase64(file);

  if (supportedImageTypes.includes(mimeType)) {
    return {
      type: "image",
      mimeType,
      data,
      metadata: { name: file.name },
    };
  }

  // Generic file block for PDF / markdown / text
  return {
    type: "file",
    mimeType,
    data,
    metadata: { filename: file.name },
  };
}

// Helper to convert File to base64 string
export async function fileToBase64(file: File): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      // Remove the data:...;base64, prefix
      resolve(result.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Type guard for Base64ContentBlock
export function isBase64ContentBlock(
  block: unknown,
): block is ContentBlock.Multimodal.Data {
  if (typeof block !== "object" || block === null || !("type" in block))
    return false;
  // file type (legacy)
  if (
    (block as { type: unknown }).type === "file" &&
    "mimeType" in block &&
    typeof (block as { mimeType?: unknown }).mimeType === "string" &&
    ((block as { mimeType: string }).mimeType.startsWith("image/") ||
      ["application/pdf", "text/markdown", "text/plain"].includes(
        (block as { mimeType: string }).mimeType,
      ))
  ) {
    return true;
  }
  // image type (new)
  if (
    (block as { type: unknown }).type === "image" &&
    "mimeType" in block &&
    typeof (block as { mimeType?: unknown }).mimeType === "string" &&
    (block as { mimeType: string }).mimeType.startsWith("image/")
  ) {
    return true;
  }
  return false;
}
