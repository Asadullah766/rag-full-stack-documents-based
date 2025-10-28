export async function uploadFile(file: File) {
  console.log("Dummy upload:", file.name);
  return { success: true };
}

export async function askQuestion(query: string) {
  console.log("Dummy query:", query);
  await new Promise((r) => setTimeout(r, 500));
  return `Fake response for: "${query}" 🤖`;
}
