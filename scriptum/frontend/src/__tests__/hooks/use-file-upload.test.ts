import { describe, it, expect } from "vitest";
import { validateFile } from "@/hooks/use-file-upload";

describe("validateFile", () => {
  it("accepts valid PDF files", () => {
    const file = new File(["content"], "paper.pdf", { type: "application/pdf" });
    expect(validateFile(file)).toBeNull();
  });

  it("accepts valid .tex files", () => {
    const file = new File(["\\documentclass{article}"], "paper.tex");
    expect(validateFile(file)).toBeNull();
  });

  it("accepts valid .bib files", () => {
    const file = new File(["@article{key}"], "refs.bib");
    expect(validateFile(file)).toBeNull();
  });

  it("rejects unsupported file types", () => {
    const file = new File(["data"], "image.png", { type: "image/png" });
    const error = validateFile(file);
    expect(error).toContain("unsupported file type");
    expect(error).toContain("image.png");
  });

  it("rejects PDF files exceeding 50 MB", () => {
    // Create a file object with a size over 50 MB
    const bigFile = new File(["x"], "big.pdf");
    Object.defineProperty(bigFile, "size", { value: 51 * 1024 * 1024 });
    const error = validateFile(bigFile);
    expect(error).toContain("exceeds the 50 MB limit");
  });

  it("rejects .tex files exceeding 10 MB", () => {
    const bigFile = new File(["x"], "big.tex");
    Object.defineProperty(bigFile, "size", { value: 11 * 1024 * 1024 });
    const error = validateFile(bigFile);
    expect(error).toContain("exceeds the 10 MB limit");
  });

  it("rejects empty files", () => {
    const emptyFile = new File([], "empty.pdf");
    Object.defineProperty(emptyFile, "size", { value: 0 });
    const error = validateFile(emptyFile);
    expect(error).toContain("is empty");
  });
});
