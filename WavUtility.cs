using System;
using System.IO;
using UnityEngine;

public static class WavUtility
{
    private const int HEADER_SIZE = 44;

    public static byte[] FromAudioClip(AudioClip clip)
    {
        using (MemoryStream stream = new MemoryStream())
        {
            using (BinaryWriter writer = new BinaryWriter(stream))
            {
                float[] samples = new float[clip.samples * clip.channels];
                clip.GetData(samples, 0);

                short[] intData = new short[samples.Length];
                byte[] bytesData = new byte[samples.Length * 2];

                int rescaleFactor = 32767;

                for (int i = 0; i < samples.Length; i++)
                {
                    intData[i] = (short)(samples[i] * rescaleFactor);
                    byte[] byteArr = BitConverter.GetBytes(intData[i]);
                    byteArr.CopyTo(bytesData, i * 2);
                }

                // 1. WAV Header
                writer.Write(new char[4] { 'R', 'I', 'F', 'F' });
                writer.Write(36 + bytesData.Length);
                writer.Write(new char[4] { 'W', 'A', 'V', 'E' });
                writer.Write(new char[4] { 'f', 'm', 't', ' ' });
                writer.Write(16); // Subchunk1Size (16 for PCM)
                writer.Write((short)1); // AudioFormat (1 for PCM)
                writer.Write((short)clip.channels);
                writer.Write(clip.frequency);
                writer.Write(clip.frequency * clip.channels * 2); // ByteRate
                writer.Write((short)(clip.channels * 2)); // BlockAlign
                writer.Write((short)16); // BitsPerSample

                // 2. Data Chunk
                writer.Write(new char[4] { 'd', 'a', 't', 'a' });
                writer.Write(bytesData.Length);
                writer.Write(bytesData);

                return stream.ToArray();
            }
        }
    }
}
