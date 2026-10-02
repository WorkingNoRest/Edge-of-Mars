using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class NPCVoiceController : MonoBehaviour
{
    [Header("Controls")]
    public KeyCode pushToTalkKey = KeyCode.V;

    [Header("Audio Output")]
    public AudioSource npcAudioSource;

    [Header("Server Route")]
    // استبدل xxxx برابط الـ Render الخاص بك
    public string backendVoiceUrl = "https://nasa-npc-backend-xxxx.onrender.com/ask_npc_voice";

    private AudioClip recordedClip;
    private string microphoneDevice;
    private bool isRecording = false;

    void Start()
    {
        if (Microphone.devices.Length > 0)
        {
            microphoneDevice = Microphone.devices[0];
        }
        else
        {
            Debug.LogError("⚠️ No microphone found on this device!");
        }

        if (npcAudioSource == null)
        {
            npcAudioSource = GetComponent<AudioSource>();
        }
    }

    void Update()
    {
        // 1. الضغط المطول على V لبدء التسجيل
        if (Input.GetKeyDown(pushToTalkKey) && !isRecording)
        {
            StartRecording();
        }

        // 2. رفع الإصبح عن V لإيقاف التسجيل وإرساله
        if (Input.GetKeyUp(pushToTalkKey) && isRecording)
        {
            StopAndSendRecording();
        }
    }

    void StartRecording()
    {
        if (string.IsNullOrEmpty(microphoneDevice)) return;

        isRecording = true;
        // التسجيل لمدة 10 ثوان كحد أقصى بجودة 44100Hz
        recordedClip = Microphone.Start(microphoneDevice, false, 10, 44100);
        Debug.Log("🎙️ Recording started... Speak now!");
    }

    void StopAndSendRecording()
    {
        if (!isRecording) return;

        int lastSamplePosition = Microphone.GetPosition(microphoneDevice);
        Microphone.End(microphoneDevice);
        isRecording = false;

        if (lastSamplePosition <= 0)
        {
            Debug.LogWarning("⚠️ Audio too short or empty.");
            return;
        }

        // قص الـ AudioClip للوقت الحقيقي الذي تم تسجيله فقط لتوفير حجم البيانات
        AudioClip trimmedClip = TrimClip(recordedClip, lastSamplePosition);
        Debug.Log("🎙️ Recording stopped. Sending to Render Server...");

        StartCoroutine(SendAudioRoutine(trimmedClip));
    }

    AudioClip TrimClip(AudioClip original, int lastSample)
    {
        float[] samples = new float[lastSample * original.channels];
        original.GetData(samples, 0);

        AudioClip newClip = AudioClip.Create("TrimmedVoice", lastSample, original.channels, original.frequency, false);
        newClip.SetData(samples, 0);
        return newClip;
    }

    IEnumerator SendAudioRoutine(AudioClip clip)
    {
        // تحويل الصوت إلى WAV Bytes عبر WavUtility
        byte[] wavBytes = WavUtility.FromAudioClip(clip);

        WWWForm form = new WWWForm();
        form.AddBinaryData("file", wavBytes, "player_speech.wav", "audio/wav");

        // استخدام GetAudioClip لاستقبال الصوت المرتجع تلقائياً من الـ Backend
        using (UnityWebRequest request = UnityWebRequestMultimedia.GetAudioClip(backendVoiceUrl, AudioType.MPEG))
        {
            // ربط الـ Multipart Form Request
            request.method = "POST";
            request.uploadHandler = new UploadHandlerRaw(form.data);
            request.uploadHandler.contentType = form.headers["Content-Type"];

            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                AudioClip responseAudio = DownloadHandlerAudioClip.GetContent(request);
                Debug.Log("🔊 Received audio response from NPC!");
                PlayNPCResponse(responseAudio);
            }
            else
            {
                Debug.LogError("❌ Request Failed: " + request.error);
            }
        }
    }

    void PlayNPCResponse(AudioClip clip)
    {
        if (npcAudioSource != null && clip != null)
        {
            npcAudioSource.clip = clip;
            npcAudioSource.Play();

            // تشغيل انيميشن الحديث لو متوفر
            Animator anim = GetComponent<Animator>();
            if (anim != null)
            {
                anim.SetTrigger("Talk");
            }
        }
    }
}
