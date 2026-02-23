import { signOut } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

export function buildConfigFetchUrl(path) {
    return `${path}?v=${Date.now()}`;
}

export async function fetchFirebaseConfig() {
    const response = await fetch(buildConfigFetchUrl("/firebase_config.json"), {
        cache: "no-store",
    });
    if (!response.ok) {
        throw new Error(`Firebase config not found: ${response.status}`);
    }
    return response.json();
}

export async function fetchAllowedEmails() {
    try {
        const response = await fetch(buildConfigFetchUrl("/allowed_emails.json"), {
            cache: "no-store",
        });
        if (!response.ok) {
            return [];
        }
        const data = await response.json();
        return (data.emails || []).map((email) => String(email).toLowerCase());
    } catch (_error) {
        return [];
    }
}

export function isAllowedEmail(email, allowedEmails) {
    const userEmail = String(email || "").toLowerCase();
    return allowedEmails.includes(userEmail);
}

export async function logoutUser(auth, onAfterSignOut) {
    try {
        await signOut(auth);
    } finally {
        if (typeof onAfterSignOut === "function") {
            onAfterSignOut();
        }
    }
}

export function showUserInfo(containerId, emailId, email) {
    const container = document.getElementById(containerId);
    const emailElement = document.getElementById(emailId);
    if (!container || !emailElement) return;
    emailElement.textContent = email;
    container.style.display = "flex";
}
